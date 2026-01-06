"""Articles.php endpoint - Homepage/Footer content router."""
import logging
import traceback
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def _write_debug_log(message: str, data: dict = None):
    """Write debug log to file in app root directory."""
    try:
        # Get app root directory (parent of app/)
        # __file__ is app/routes/feed/articles.py
        # .parent = app/routes/feed/
        # .parent.parent = app/routes/
        # .parent.parent.parent = app/
        # .parent.parent.parent.parent = root/
        app_root = Path(__file__).parent.parent.parent.parent
        debug_log_path = app_root / "debug.log"
        
        import json
        import os
        from datetime import datetime
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "data": data or {}
        }
        
        # Write to file (creates file if it doesn't exist)
        # Use 'a' mode (append) - file will be created if it doesn't exist
        with open(str(debug_log_path), "a", encoding="utf-8") as f:
            json_str = json.dumps(log_entry) + "\n"
            bytes_written = f.write(json_str)
            f.flush()  # Ensure data is written immediately
            os.fsync(f.fileno())  # Force write to disk
        
        # Log success to standard logger for verification
        logger.info(f"Debug log written: {bytes_written} bytes to {debug_log_path}")
    except PermissionError as e:
        # Log permission errors to standard logger
        logger.error(f"Permission denied writing debug log to {debug_log_path}: {e}")
    except Exception as e:
        # Log other errors to standard logger as fallback
        logger.error(f"Failed to write debug log to {debug_log_path}: {e}")
        import traceback
        logger.error(traceback.format_exc())

try:
    from fastapi import APIRouter, Request, Query, HTTPException
    from fastapi.responses import HTMLResponse, PlainTextResponse
    from typing import Optional
except Exception as e:
    logger.error(f"Failed to import FastAPI components: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    from app.database import db
except Exception as e:
    logger.error(f"Failed to import app.database: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    from app.services.content import build_footer_wp, build_page_wp, get_header_footer, build_metaheader, wrap_content_with_header_footer
except Exception as e:
    logger.error(f"Failed to import app.services.content: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    from app.utils.logging import log_post_variables
except Exception as e:
    logger.error(f"Failed to import app.utils.logging: {e}")
    logger.error(traceback.format_exc())
    # Don't raise - logging is optional
    log_post_variables = None

router = APIRouter()


@router.api_route("/Articles.php", methods=["GET", "POST"])
async def articles_endpoint(
    request: Request,
    # Query parameters (for GET and POST with query string)
    domain: Optional[str] = Query(None, alias="domain"),
    Action: Optional[str] = Query(None),
    agent: Optional[str] = Query(None),
    pageid: Optional[str] = Query(None),
    k: Optional[str] = Query(None),
    referer: Optional[str] = Query(None),
    address: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    uri: Optional[str] = Query(None),
    cScript: Optional[str] = Query(None),
    version: Optional[str] = Query("1.0"),
    blnComplete: Optional[str] = Query(None),
    page: Optional[str] = Query("1"),
    city: Optional[str] = Query(None),
    cty: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    st: Optional[str] = Query(None),
    nocache: Optional[str] = Query("0"),
):
    """
    Articles.php endpoint - generates homepage/footer content when Action is empty.
    Replicates the PHP Articles.php functionality.
    Handles both GET and POST requests (PHP $_REQUEST gets both).
    """
    # Initialize variables for logging
    form_data = None
    raw_body = None
    
    # For POST requests, also check form data and JSON body
    if request.method == "POST":
        query_params = dict(request.query_params)
        
        # Update parameters from query string
        domain = domain or query_params.get("domain")
        Action = Action or query_params.get("Action")
        agent = agent or query_params.get("agent")
        pageid = pageid or query_params.get("pageid")
        k = k or query_params.get("k")
        referer = referer or query_params.get("referer")
        address = address or query_params.get("address")
        query = query or query_params.get("query")
        uri = uri or query_params.get("uri")
        cScript = cScript or query_params.get("cScript")
        version = version or query_params.get("version", "1.0")
        blnComplete = blnComplete or query_params.get("blnComplete")
        page = page or query_params.get("page", "1")
        city = city or query_params.get("city")
        cty = cty or query_params.get("cty")
        state = state or query_params.get("state")
        st = st or query_params.get("st")
        nocache = nocache or query_params.get("nocache", "0")
        
        # Try to parse body as form data or JSON
        content_type = request.headers.get("content-type", "")
        
        try:
            raw_body = await request.body()
            if raw_body:
                if "application/json" in content_type:
                    try:
                        json_data = await request.json()
                        domain = domain or json_data.get("domain")
                        Action = Action or json_data.get("Action")
                        agent = agent or json_data.get("agent")
                        pageid = pageid or json_data.get("pageid")
                        k = k or json_data.get("k")
                        referer = referer or json_data.get("referer")
                        address = address or json_data.get("address")
                        query = query or json_data.get("query")
                        uri = uri or json_data.get("uri")
                        cScript = cScript or json_data.get("cScript")
                        version = version or json_data.get("version", "1.0")
                        blnComplete = blnComplete or json_data.get("blnComplete")
                        page = page or json_data.get("page", "1")
                        city = city or json_data.get("city")
                        cty = cty or json_data.get("cty")
                        state = state or json_data.get("state")
                        st = st or json_data.get("st")
                        nocache = nocache or json_data.get("nocache", "0")
                    except Exception:
                        pass
                else:
                    # Try form data
                    try:
                        form_data = await request.form()
                        domain = domain or form_data.get("domain")
                        Action = Action or form_data.get("Action")
                        agent = agent or form_data.get("agent")
                        pageid = pageid or form_data.get("pageid")
                        k = k or form_data.get("k")
                        referer = referer or form_data.get("referer")
                        address = address or form_data.get("address")
                        query = query or form_data.get("query")
                        uri = uri or form_data.get("uri")
                        cScript = cScript or form_data.get("cScript")
                        version = version or form_data.get("version", "1.0")
                        blnComplete = blnComplete or form_data.get("blnComplete")
                        page = page or form_data.get("page", "1")
                        city = city or form_data.get("city")
                        cty = cty or form_data.get("cty")
                        state = state or form_data.get("state")
                        st = st or form_data.get("st")
                        nocache = nocache or form_data.get("nocache", "0")
                    except Exception:
                        # Fallback: try to parse as URL-encoded string
                        try:
                            from urllib.parse import parse_qs, unquote
                            body_str = raw_body.decode('utf-8')
                            # Handle both raw string and URL-encoded
                            if '=' in body_str:
                                parsed = parse_qs(body_str)
                                domain = domain or (parsed.get("domain", [None])[0])
                                Action = Action or (parsed.get("Action", [None])[0])
                                agent = agent or (parsed.get("agent", [None])[0])
                                pageid = pageid or (parsed.get("pageid", [None])[0])
                                k = k or (parsed.get("k", [None])[0])
                                referer = referer or (parsed.get("referer", [None])[0])
                                address = address or (parsed.get("address", [None])[0])
                                query = query or (parsed.get("query", [None])[0])
                                uri = uri or (parsed.get("uri", [None])[0])
                                cScript = cScript or (parsed.get("cScript", [None])[0])
                                version = version or (parsed.get("version", ["1.0"])[0])
                                blnComplete = blnComplete or (parsed.get("blnComplete", [None])[0])
                                page = page or (parsed.get("page", ["1"])[0])
                                city = city or (parsed.get("city", [None])[0])
                                cty = cty or (parsed.get("cty", [None])[0])
                                state = state or (parsed.get("state", [None])[0])
                                st = st or (parsed.get("st", [None])[0])
                                nocache = nocache or (parsed.get("nocache", ["0"])[0])
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Could not parse POST body: {e}")
    
    # Log POST variables for debugging
    if log_post_variables:
        try:
            # Get URL
            url = str(request.url)
            
            # Get query params as dict
            query_params_dict = dict(request.query_params)
            
            # Convert form_data to dict if it exists
            form_data_dict = None
            if form_data:
                try:
                    form_data_dict = dict(form_data)
                except Exception:
                    form_data_dict = None
            
            # Get raw body as string if form_data is None
            raw_body_str = None
            if not form_data_dict and raw_body:
                try:
                    raw_body_str = raw_body.decode('utf-8')
                except Exception:
                    raw_body_str = None
            
            # Get headers
            headers_dict = dict(request.headers)
            
            # Call logging function
            log_post_variables(
                endpoint="Articles.php",
                method=request.method,
                url=url,
                query_params=query_params_dict,
                form_data=form_data_dict,
                json_data=None,  # Articles.php doesn't use json_data
                raw_body=raw_body_str,
                headers=headers_dict
            )
        except Exception as e:
            # Don't let logging errors break the endpoint
            logger.warning(f"Failed to log POST variables: {e}")
    
    # Normalize Action - treat empty string as None/empty
    # Check if Action is empty string from any source (GET query, POST form, POST JSON)
    if Action == "" or (isinstance(Action, str) and Action.strip() == ""):
        Action = None
    
    # Handle CheckFiles endpoint (case-insensitive) - public health check
    # This must be checked before domain validation to allow public access
    if Action and isinstance(Action, str) and Action.lower() == "checkfiles":
        return PlainTextResponse(content="FRL CheckFiles OK")
    
    # PHP Articles.php requires domain and agent parameters
    if not domain:
        raise HTTPException(status_code=400, detail="Domain parameter required")
    
    if not agent:
        raise HTTPException(status_code=400, detail="Agent parameter required")
    
    # Validate domain exists
    domain_data = db.fetch_row(
        "SELECT id FROM bwp_domains WHERE domain_name = %s AND deleted != 1",
        (domain,)
    )
    
    if not domain_data:
        # PHP returns empty/404 for invalid domains
        error_msg = f"Articles.php: Invalid domain '{domain}' - not found in database"
        logger.warning(error_msg)
        logger.info(f"Calling _write_debug_log for invalid domain: {domain}")
        _write_debug_log(error_msg, {"domain": domain, "status_code": 404, "error_type": "invalid_domain"})
        return HTMLResponse(content="<!-- Invalid Domain -->", status_code=404)
    
    domainid = domain_data['id']
    
    # Get full domain data (PHP line 98-103)
    domain_full_sql = """
        SELECT d.*, s.servicetype, s.keywords as service_keywords, d.script_version, d.wp_plugin, d.iswin, d.usepurl, d.webworkscms
        FROM bwp_domains d
        LEFT JOIN bwp_services s ON d.servicetype = s.id
        WHERE d.id = %s AND d.deleted != 1
    """
    domain_category = db.fetch_row(domain_full_sql, (domainid,))
    
    if not domain_category:
        # This should rarely happen - domain exists but full query fails
        error_msg = f"Articles.php: Domain '{domain}' (id={domainid}) found but domain_category query returned no results"
        logger.warning(error_msg)
        logger.info(f"Calling _write_debug_log for domain_category_not_found: {domain} (id={domainid})")
        _write_debug_log(error_msg, {"domain": domain, "domainid": domainid, "status_code": 404, "error_type": "domain_category_not_found"})
        return HTMLResponse(content="<!-- Domain not found -->", status_code=404)
    
    # Check domain status
    domain_status = domain_category.get('status')
    if domain_status == 6:  # Rejected
        return HTMLResponse(content="<!-- Domain Rejected -->", status_code=403)
    
    # Get domain settings
    domain_settings = db.fetch_row(
        "SELECT * FROM bwp_domain_settings WHERE domainid = %s",
        (domainid,)
    )
    
    if not domain_settings:
        db.execute(
            "INSERT INTO bwp_domain_settings SET domainid = %s",
            (domainid,)
        )
        domain_settings = db.fetch_row(
            "SELECT * FROM bwp_domain_settings WHERE domainid = %s",
            (domainid,)
        )
    
    # PHP Articles.php line 260-294: Check for webworkscms and redirect to CMS homepage
    webworkscms = domain_category.get('webworkscms') or 0
    if webworkscms == 1:
        cms_sql = "SELECT * FROM bwp_cms WHERE domainid = %s"
        cms = db.fetch_row(cms_sql, (domainid,))
        
        if cms and cms.get('cmsactive') == 1:
            cmspagetype = cms.get('cmspagetype')
            cmspage = cms.get('cmspage')
            
            if cmspagetype == 1 and cmspage:
                # Determine which page ID to use:
                # - If Action is set, use pageid (PageID) from request as the article ID
                # - If Action is empty, use cmspage as the homepage ID
                action_empty = not Action or (isinstance(Action, str) and Action.strip() == '')
                
                if action_empty:
                    # Action is empty - use cmspage as the homepage
                    page_id_to_use = cmspage
                    # Get article from bwp_bubblefeed for keyword data
                    article_sql = "SELECT * FROM bwp_bubblefeed WHERE id = %s"
                    article = db.fetch_row(article_sql, (cmspage,))
                else:
                    # Action is set - use pageid (PageID) from request as the article ID
                    if pageid:
                        try:
                            page_id_to_use = int(pageid)
                        except (ValueError, TypeError):
                            page_id_to_use = cmspage  # Fallback to cmspage if pageid is invalid
                    else:
                        page_id_to_use = cmspage  # Fallback to cmspage if pageid is not provided
                    
                    # Get article from bwp_bubblefeed using the pageid
                    article_sql = "SELECT * FROM bwp_bubblefeed WHERE id = %s"
                    article = db.fetch_row(article_sql, (page_id_to_use,))
                
                # Use article data for keyword if found
                keyword_text = article.get('restitle', '') if article else ''
                
                # Build the page using build_page_wp
                page_content = build_page_wp(
                    bubbleid=page_id_to_use,  # Use determined page ID (pageid if Action set, cmspage if Action empty)
                    domainid=domainid,
                    agent=agent or '',
                    keyword=keyword_text,
                    domain_data=domain_category,
                    domain_settings=domain_settings,
                    artpageid=page_id_to_use,
                    artdomainid=domainid
                )
                
                # Get header and footer
                header_data = get_header_footer(domainid, domain_category.get('status'))
                header = header_data['header']
                footer = header_data['footer']
                
                # Build metaheader
                metaheader = build_metaheader(
                    domainid=domainid,
                    domain_data=domain_category,
                    domain_settings=domain_settings,
                    action='1',
                    keyword=keyword_text,
                    pageid=page_id_to_use,  # Use determined page ID
                    city=city or cty or '',
                    state=state or st or ''
                )
                
                # Build canonical URL
                if domain_category.get('ishttps') == 1:
                    canonical_url = 'https://'
                else:
                    canonical_url = 'http://'
                if domain_category.get('usewww') == 1:
                    canonical_url += 'www.' + domain_category.get('domain_name', '')
                else:
                    canonical_url += domain_category.get('domain_name', '')
                canonical_url += '/'
                
                # Wrap content with header and footer
                full_page_html = wrap_content_with_header_footer(
                    content=page_content,
                    header=header,
                    footer=footer,
                    metaheader=metaheader,
                    canonical_url=canonical_url,
                    websitereferencesimple=False,
                    wp_plugin=domain_category.get('wp_plugin', 0)
                )
                
                # PHP Articles.php includes feed-home.css.php at lines 255 and 471
                # Add feed-home.css.php CSS before </head> or at the end of <head>
                feed_home_css = '''<style type="text/css">
ul.mdubgwi-footer-nav {margin:0 auto !important;padding: 0px !important;overflow:visible !important}

#mdubgwi-hidden-button {  height:0px !important; width:0px !important;	 }

.mdubgwi-button { display:block!important; visibility:visible!important; height:20px !important; width:250px !important; margin:0px !important; padding:0 !important; }

.mdubgwi-footer-section {z-index: 99999999 !important; overflow:visible !important; display:block !important; position: relative !important; bottom: 0px !important; width: 250px !important; margin:0 auto !important; }
.mdubgwi-footer-section.plain ul {list-style: none !important; margin:0 auto !important; text-align:center!important;}

.mdubgwi-footer-nav li ul li {border:none !important;overflow-x: visible !important;overflow-y: visible !important;text-align:center !important; margin:0px !important;position: relative!important; color: #00397c !important; padding:0px !important; display:block !important; }
.mdubgwi-footer-section.num-plain li {list-style: none !important; display:inline !important;}
.num-lite li ul  { position: absolute !important; bottom: 45px !important; }
.mdubgwi-footer-nav li ul  {position: absolute !important;left:53% !important; min-width:100px !important; -ms-filter: "progid:DXImageTransform.Microsoft.Alpha(Opacity=0.8)" !important; -moz-opacity: 0.8 !important; -khtml-opacity: 0.8 ! important!important;  opacity: 0.8 !important; font-size: 13px !important;  float:none !important; margin:0px !important;  list-style: none !important; line-height: 18px !important; background: #fff !important; display: none !important; visibility: hidden !important; z-index: -1 !important; }
.mdubgwi-sub-nav {width:450px;}
.mdubgwi-footer-nav li ul li ul {min-width:450px !important; -ms-filter: "progid:DXImageTransform.Microsoft.Alpha(Opacity=0.8)" !important; -moz-opacity: 0.8 !important; -khtml-opacity: 0.8 ! important!important;  opacity: 0.8 !important; font-size: 13px !important;  float:none !important; margin:0px !important;  list-style: none !important; line-height: 18px !important; background: #fff !important; display: none !important; visibility: hidden !important; z-index: -1 !important; }
.mdubgwi-footer-nav:hover li ul {-ms-filter: "progid:DXImageTransform.Microsoft.Alpha(Opacity=0.8)" !important; -moz-opacity: 0.8 !important; -khtml-opacity: 0.8 ! important!important;  opacity: 0.8 !important; list-style:none !important; display: block !important; visibility: visible !important; z-index: 999999 !important; }
.mdubgwi-footer-nav:hover li ul li ul {min-width:450px !important; -ms-filter: "progid:DXImageTransform.Microsoft.Alpha(Opacity=0.8)" !important; -moz-opacity: 0.8 !important; -khtml-opacity: 0.8 ! important!important;  opacity: 0.8 !important; font-size: 13px !important;  float:none !important; margin:0px !important;  list-style: none !important; line-height: 18px !important; background: #fff !important; display: none !important; visibility: hidden !important; z-index: -1 !important; }
.mdubgwi-footer-nav li a {background:transparent !important; padding:5px 5px !important;text-align:center !important;  text-decoration:none !important; border:0 !important; line-height: 18px !important; font-size:13px !important; color: #00397c; }
.mdubgwi-footer-nav li {list-style:none !important; background:transparent !important; padding:5px 5px !important;text-align:center !important;  color: #00397c; text-decoration:none !important; border:0 !important; line-height: 18px !important; font-size:13px !important; }
.mdubgwi-footer-nav li ul { padding:5px 5px 10px 5px !important; margin:0 !important; }
.mdubgwi-footer-nav li ul:hover {-ms-filter: "progid:DXImageTransform.Microsoft.Alpha(Opacity=1.0)" !important; -moz-opacity: 1.0 !important; -khtml-opacity: 1.0 ! important!important;  opacity: 1.0 !important;      -webkit-transition: opacity 1s ease!important;     -moz-transition: opacity 1s ease!important;     -o-transition: opacity 1s ease!important;     -ms-transition: opacity 1s ease!important;        transition: opacity 1s ease!important;  list-style:none !important; display: block !important; visibility: visible !important; z-index: 999999 !important; }
.mdubgwi-footer-nav li ul:hover li ul {min-width: 450px !important; -ms-filter: "progid:DXImageTransform.Microsoft.Alpha(Opacity=0.8)" !important; -moz-opacity: 0.8 !important; -khtml-opacity: 0.8 ! important;  opacity: 0.8 !important; font-size: 13px !important;  float:none !important; margin:0px !important;  list-style: none !important; line-height: 18px !important; background: #fff !important; display: none !important; visibility: hidden !important; z-index: -1 !important; }
.mdubgwi-footer-nav li ul li {border:none !important;background:transparent !important;overflow-x: visible !important;overflow-y: visible !important; text-align: center !important;margin:0px !important; position: relative!important; list-style:none !important; }
.mdubgwi-footer-nav li ul li:hover ul{ display: block !important; visibility: visible !important; z-index: 999999 !important; -webkit-transition: all 1s ease-out!important; -moz-transition: all 1s ease-out!important; -o-transition: all 1s ease-out!important; -ms-transition: all 1s ease-out!important; transition: all 1s ease-out!important;}
.mdubgwi-footer-nav li ul li ul {border:none !important;bottom:0px !important;padding: 5px 5px 15px 5px !important;  -webkit-transition: all 1s ease-out!important; -moz-transition: all 1s ease-out!important; -o-transition: all 1s ease-out!important; -ms-transition: all 1s ease-out!important; transition: all 1s ease-out!important;position: absolute !important; }
.mdubgwi-footer-nav li ul li ul li {border:none !important; background:transparent !important; overflow-x: visible !important;overflow-y: visible !important;left:0 !important; text-align: center !important;margin:0px !important; list-style:none !important; padding:0px 5px !important; }
.ngodkrbsitr-spacer { clear:both!important; height:5px !important; display:block!important;width:100%!important; }
.ngodkrbsitr-social { margin: 0 3px !important; padding: 0px !important; float:left!important;	 }
.align-left { float:left!important; border:0!important; margin-right:1% !important; margin-bottom:10px !important; }
.align-right { float:right!important; border:0!important; margin-left:1% !important; text-align:right!important; margin-bottom:10px !important; }
img.align-left { max-width:100%!important;" }
.mdubgwi-sub-nav li ul  {display:none !important; visibility:hidden !important;}
.mdubgwi-sub-nav li:hover ul {display:block !important; visibility:visible !important;}
</style>
'''
                
                # Insert feed-home.css.php CSS before </head>
                if '</head>' in full_page_html:
                    head_pos = full_page_html.lower().find('</head>')
                    full_page_html = full_page_html[:head_pos] + feed_home_css + full_page_html[head_pos:]
                else:
                    # If no </head> found, append to the end
                    full_page_html += feed_home_css
                
                return HTMLResponse(content=full_page_html)
            
            elif cmspagetype == 5 and cmspage:
                # Get article from bwp_blog_post (Action=5 - not yet implemented)
                # For now, return a placeholder
                return HTMLResponse(content="<!-- CMS Blog Post (Action=5) not yet implemented -->")
        
    
    # PHP Articles.php: if script_version >= 3 and wp_plugin != 1 and iswin != 1 and usepurl != 0
    # then call seo_automation_build_footer30 (similar to build_footer_wp)
    script_version_str = domain_category.get('script_version', '0') or '0'
    try:
        if isinstance(script_version_str, str):
            parts = script_version_str.split('.')
            script_version = float(parts[0] + '.' + parts[1] if len(parts) > 1 else parts[0])
        else:
            script_version = float(script_version_str)
    except (ValueError, IndexError, TypeError):
        script_version = 0.0
    
    wp_plugin = domain_category.get('wp_plugin') or 0
    iswin = domain_category.get('iswin') or 0
    usepurl = domain_category.get('usepurl') or 0
    
    # PHP line 172: if($domains['script_version'] >= 3 && $domains['wp_plugin'] != 1 && $domains['iswin'] != 1 && $domains['usepurl'] != 0)
    if script_version >= 3 and wp_plugin != 1 and iswin != 1 and usepurl != 0:
        # Generate footer HTML (similar to Articles30.php seo_automation_build_footer30)
        footer_html = build_footer_wp(domainid, domain_category, domain_settings)
        # For now, just return the footer HTML
        return HTMLResponse(content=footer_html)
    
    # When Action is empty, generate footer HTML for non-CMS sites
    # Check if Action is empty (None or empty string) - also check if Action key exists in query params
    action_in_query = "Action" in request.query_params
    action_from_query = request.query_params.get("Action")
    action_empty = (
        not Action or 
        (isinstance(Action, str) and Action.strip() == '') or
        (action_in_query and (action_from_query is None or action_from_query == ""))
    )
    
    if action_empty and webworkscms != 1:
        # Generate footer HTML for non-CMS sites when Action is empty
        footer_html = build_footer_wp(domainid, domain_category, domain_settings)
        return HTMLResponse(content=footer_html)
    
    # For other cases, return a basic response
    # PHP Articles.php has complex logic for generating homepage content with links, etc.
    # This is a simplified version - full implementation would require more PHP code review
    return HTMLResponse(content="<!-- Articles.php - Action not empty or conditions not met -->")

