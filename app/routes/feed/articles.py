"""Articles.php endpoint - Homepage/Footer content router."""
import logging
import traceback

logger = logging.getLogger(__name__)

try:
    from fastapi import APIRouter, Request, Query, HTTPException
    from fastapi.responses import HTMLResponse
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
    # #region agent log
    try:
        import json
        import os
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"articles.py:60","message":"Function entry - initial Action from FastAPI Query","data":{"Action":str(Action) if Action is not None else None,"Action_type":type(Action).__name__,"method":request.method},"timestamp":int(__import__("time").time()*1000)})+"\n")
    except Exception:
        pass
    # #endregion
    
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
    
    # Normalize Action - treat empty string as None/empty
    # Check if Action is empty string from any source (GET query, POST form, POST JSON)
    # #region agent log
    action_before_norm = Action
    # #endregion
    if Action == "" or (isinstance(Action, str) and Action.strip() == ""):
        Action = None
    # #region agent log
    try:
        import os
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"articles.py:171","message":"After normalization","data":{"Action_before":str(action_before_norm) if action_before_norm is not None else None,"Action_after":str(Action) if Action is not None else None},"timestamp":int(__import__("time").time()*1000)})+"\n")
    except Exception:
        pass
    # #endregion
    
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
    # #region agent log
    try:
        import os
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"articles.py:227","message":"Domain category loaded","data":{"webworkscms":webworkscms,"script_version":str(domain_category.get('script_version', '0'))},"timestamp":int(__import__("time").time()*1000)})+"\n")
    except Exception:
        pass
    # #endregion
    if webworkscms == 1:
        cms_sql = "SELECT * FROM bwp_cms WHERE domainid = %s"
        cms = db.fetch_row(cms_sql, (domainid,))
        # #region agent log
        try:
            import os
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "debug.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"articles.py:260","message":"CMS check","data":{"cms_exists":cms is not None,"cmsactive":cms.get('cmsactive') if cms else None,"cmspagetype":cms.get('cmspagetype') if cms else None,"cmspage":cms.get('cmspage') if cms else None},"timestamp":int(__import__("time").time()*1000)})+"\n")
        except Exception:
            pass
        # #endregion
        
        if cms and cms.get('cmsactive') == 1:
            cmspagetype = cms.get('cmspagetype')
            cmspage = cms.get('cmspage')
            
            if cmspagetype == 1 and cmspage:
                # Get article from bwp_bubblefeed
                article_sql = "SELECT * FROM bwp_bubblefeed WHERE id = %s"
                article = db.fetch_row(article_sql, (cmspage,))
                # #region agent log
                try:
                    import os
                    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "debug.log")
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"articles.py:269","message":"Article lookup for CMS","data":{"cmspage":cmspage,"article_found":article is not None},"timestamp":int(__import__("time").time()*1000)})+"\n")
                except Exception:
                    pass
                # #endregion
                
                if article:
                    # Redirect to Article.php with Action=1 and the article's restitle and PageID
                    # PHP uses curl_get_file_contents, but we'll call the handler directly
                    # Build the article page content
                    keyword_slug = article.get('restitle', '').replace(' ', '-').lower()
                    bubbleid = article.get('id', 0)
                    
                    # Build the page using build_page_wp
                    page_content = build_page_wp(
                        bubbleid=bubbleid,
                        domainid=domainid,
                        agent=agent or '',
                        keyword=article.get('restitle', ''),
                        domain_data=domain_category,
                        domain_settings=domain_settings,
                        artpageid=cmspage,
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
                        keyword=article.get('restitle', ''),
                        pageid=cmspage,
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
        
        # For CMS sites with empty Action, if CMS conditions aren't met, return empty content
        # CMS sites handle their own content, so we return empty when Action is empty
        # Check if Action is empty
        action_in_query = "Action" in request.query_params
        action_from_query = request.query_params.get("Action")
        action_empty = (
            not Action or 
            (isinstance(Action, str) and Action.strip() == '') or
            (action_in_query and (action_from_query is None or action_from_query == ""))
        )
        # #region agent log
        try:
            import os
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "debug.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"articles.py:401","message":"CMS fallback check","data":{"action_empty":action_empty,"cms_exists":cms is not None,"cmsactive":cms.get('cmsactive') if cms else None},"timestamp":int(__import__("time").time()*1000)})+"\n")
        except Exception:
            pass
        # #endregion
        
        if action_empty:
            # For CMS sites with empty Action, generate footer HTML
            # #region agent log
            try:
                import os
                log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "debug.log")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"articles.py:414","message":"Returning footer for CMS site with empty Action","data":{},"timestamp":int(__import__("time").time()*1000)})+"\n")
            except Exception:
                pass
            # #endregion
            footer_html = build_footer_wp(domainid, domain_category, domain_settings)
            return HTMLResponse(content=footer_html)
    
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
    # #region agent log
    try:
        import os
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"articles.py:369","message":"Before script_version check","data":{"script_version":script_version,"wp_plugin":wp_plugin,"iswin":iswin,"usepurl":usepurl,"condition_result":script_version >= 3 and wp_plugin != 1 and iswin != 1 and usepurl != 0},"timestamp":int(__import__("time").time()*1000)})+"\n")
    except Exception:
        pass
    # #endregion
    if script_version >= 3 and wp_plugin != 1 and iswin != 1 and usepurl != 0:
        # Generate footer HTML (similar to Articles30.php seo_automation_build_footer30)
        footer_html = build_footer_wp(domainid, domain_category, domain_settings)
        # #region agent log
        try:
            import os
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "debug.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"articles.py:373","message":"Returning footer from script_version check","data":{},"timestamp":int(__import__("time").time()*1000)})+"\n")
        except Exception:
            pass
        # #endregion
        # For now, just return the footer HTML
        return HTMLResponse(content=footer_html)
    
    # When Action is empty, generate footer HTML for non-CMS sites
    # Check if Action is empty (None or empty string) - also check if Action key exists in query params
    action_in_query = "Action" in request.query_params
    action_from_query = request.query_params.get("Action")
    # #region agent log
    try:
        import os
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"articles.py:377","message":"Before empty check","data":{"Action":str(Action) if Action is not None else None,"action_in_query":action_in_query,"action_from_query":str(action_from_query) if action_from_query is not None else None,"query_params_keys":list(request.query_params.keys())},"timestamp":int(__import__("time").time()*1000)})+"\n")
    except Exception:
        pass
    # #endregion
    action_empty = (
        not Action or 
        (isinstance(Action, str) and Action.strip() == '') or
        (action_in_query and (action_from_query is None or action_from_query == ""))
    )
    # #region agent log
    try:
        import os
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"articles.py:384","message":"Empty check result","data":{"action_empty":action_empty,"webworkscms":webworkscms,"webworkscms_not_1":webworkscms != 1,"will_generate_footer":action_empty and webworkscms != 1},"timestamp":int(__import__("time").time()*1000)})+"\n")
    except Exception:
        pass
    # #endregion
    
    if action_empty and webworkscms != 1:
        # Generate footer HTML for non-CMS sites when Action is empty
        footer_html = build_footer_wp(domainid, domain_category, domain_settings)
        return HTMLResponse(content=footer_html)
    
    # For other cases, return a basic response
    # PHP Articles.php has complex logic for generating homepage content with links, etc.
    # This is a simplified version - full implementation would require more PHP code review
    # #region agent log
    try:
        import os
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"articles.py:393","message":"Returning error - no conditions met","data":{"Action":str(Action) if Action is not None else None,"action_empty":action_empty,"webworkscms":webworkscms},"timestamp":int(__import__("time").time()*1000)})+"\n")
    except Exception:
        pass
    # #endregion
    return HTMLResponse(content="<!-- Articles.php - Action not empty or conditions not met -->")

