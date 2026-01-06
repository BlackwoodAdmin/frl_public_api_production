"""Article.php endpoint - Main content router."""
import logging
import traceback

logger = logging.getLogger(__name__)

try:
    from fastapi import APIRouter, Request, Query, HTTPException, Form
    from fastapi.responses import JSONResponse, HTMLResponse, Response, PlainTextResponse
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
    from app.services.auth import validate_api_credentials
except Exception as e:
    logger.error(f"Failed to import app.services.auth: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    from app.services.content import build_footer_wp, build_pages_array, clean_title, seo_filter_text_custom, to_ascii
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


@router.api_route("/Article.php", methods=["GET", "POST"])
async def article_endpoint(
    request: Request,
    # Query parameters (for GET and POST with query string)
    domain: Optional[str] = Query(None, alias="domain"),
    Action: Optional[str] = Query(None),
    apiid: Optional[str] = Query(None),
    apikey: Optional[str] = Query(None),
    kkyy: Optional[str] = Query(None),
    feededit: Optional[str] = Query(None),
    k: Optional[str] = Query(None),
    key: Optional[str] = Query(None),
    pageid: Optional[str] = Query(None),
    version: Optional[str] = Query("1.0"),
    agent: Optional[str] = Query(None),
    # PHP plugin 0308.php parameters
    referer: Optional[str] = Query(None),
    address: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    uri: Optional[str] = Query(None),
    cScript: Optional[str] = Query(None),
    blnComplete: Optional[str] = Query(None),
    page: Optional[str] = Query("1"),
    city: Optional[str] = Query(None),
    cty: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    st: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    c: Optional[str] = Query(None),  # Alternative category parameter
):
    """
    Main Article.php endpoint - routes to different handlers based on parameters.
    Replicates the PHP Article.php functionality.
    Handles both GET and POST requests (PHP $_REQUEST gets both).
    """
    
    # For POST requests, also check form data and JSON body (PHP $_REQUEST includes both GET and POST)
    # Note: POST requests can have parameters in query string OR body
    form_data = None
    json_data = None
    if request.method == "POST":
        # First, check query params (POST requests can have params in URL too)
        # PHP $_REQUEST merges $_GET and $_POST, so we check both
        query_params = dict(request.query_params)
        
        # Update parameters from query string (POST can have params in URL)
        # Use query params as base, then override with body if present
        domain = domain or query_params.get("domain")
        Action = Action or query_params.get("Action")
        apiid = apiid or query_params.get("apiid")
        apikey = apikey or query_params.get("apikey")
        kkyy = kkyy or query_params.get("kkyy")
        feededit = feededit or query_params.get("feedit")
        k = k or query_params.get("k")
        key = key or query_params.get("key")
        pageid = pageid or query_params.get("pageid")
        version = version or query_params.get("version", "1.0")
        agent = agent or query_params.get("agent")
        # PHP plugin 0308.php parameters
        referer = referer or query_params.get("referer")
        address = address or query_params.get("address")
        query = query or query_params.get("query")
        uri = uri or query_params.get("uri")
        cScript = cScript or query_params.get("cScript")
        blnComplete = blnComplete or query_params.get("blnComplete")
        page = page or query_params.get("page", "1")
        city = city or query_params.get("city")
        cty = cty or query_params.get("cty")
        state = state or query_params.get("state")
        st = st or query_params.get("st")
        category = category or query_params.get("category")
        c = c or query_params.get("c")
        
        # Then try to parse body as form data or JSON (PHP $_REQUEST includes both GET and POST)
        content_type = request.headers.get("content-type", "")
        
        # Read raw body first to see what we're getting
        try:
            raw_body = await request.body()
        except Exception as e:
            logger.warning(f"Could not read raw body: {e}")
            raw_body = b""
        
        # Try to parse body - WordPress uses cURL with CURLOPT_POSTFIELDS (form-encoded)
        # Try form data first (most common for WordPress POST requests)
        # If no content-type, assume form-encoded (WordPress cURL default)
        try:
            if "application/json" in content_type:
                # Only try JSON if explicitly JSON content type
                try:
                    json_data = await request.json()
                    if json_data.get("domain"):
                        domain = json_data.get("domain")
                    if json_data.get("Action"):
                        Action = json_data.get("Action")
                    if json_data.get("apiid"):
                        apiid = json_data.get("apiid")
                    if json_data.get("apikey"):
                        apikey = json_data.get("apikey")
                    if json_data.get("kkyy"):
                        kkyy = json_data.get("kkyy")
                    if json_data.get("feedit"):
                        feededit = json_data.get("feedit")
                    if json_data.get("k"):
                        k = json_data.get("k")
                    if json_data.get("key"):
                        key = json_data.get("key")
                    if json_data.get("pageid"):
                        pageid = json_data.get("pageid")
                    if json_data.get("version"):
                        version = json_data.get("version")
                    if json_data.get("agent"):
                        agent = json_data.get("agent")
                    if json_data.get("category"):
                        category = json_data.get("category")
                    if json_data.get("c"):
                        c = json_data.get("c")
                except Exception as e2:
                    logger.warning(f"JSON parsing failed: {e2}")
            else:
                # Try form data (default for WordPress cURL POST requests)
                # This handles: application/x-www-form-urlencoded, multipart/form-data, or no content-type
                try:
                    form_data = await request.form()
                    form_dict = dict(form_data)
                    # Override with form data if present (POST body takes precedence)
                    if form_data.get("domain"):
                        domain = form_data.get("domain")
                    if form_data.get("Action"):
                        Action = form_data.get("Action")
                    if form_data.get("apiid"):
                        apiid = form_data.get("apiid")
                    if form_data.get("apikey"):
                        apikey = form_data.get("apikey")
                    if form_data.get("kkyy"):
                        kkyy = form_data.get("kkyy")
                    if form_data.get("feedit"):
                        feededit = form_data.get("feedit")
                    if form_data.get("k"):
                        k = form_data.get("k")
                    if form_data.get("key"):
                        key = form_data.get("key")
                    if form_data.get("pageid"):
                        pageid = form_data.get("pageid")
                    if form_data.get("version"):
                        version = form_data.get("version")
                    if form_data.get("agent"):
                        agent = form_data.get("agent")
                    if form_data.get("category"):
                        category = form_data.get("category")
                    if form_data.get("c"):
                        c = form_data.get("c")
                except Exception as e:
                    logger.warning(f"Form data parsing failed: {e}")
                    # If form parsing fails, try to parse raw body as URL-encoded string
                    if raw_body:
                        try:
                            from urllib.parse import parse_qs, unquote
                            body_str = raw_body.decode('utf-8')
                            # Parse URL-encoded string
                            parsed = parse_qs(body_str)
                            # Extract first value from each list (parse_qs returns lists)
                            if parsed.get("domain"):
                                domain = parsed.get("domain")[0]
                            if parsed.get("Action"):
                                Action = parsed.get("Action")[0]
                            if parsed.get("apiid"):
                                apiid = parsed.get("apiid")[0]
                            if parsed.get("apikey"):
                                apikey = parsed.get("apikey")[0]
                            if parsed.get("kkyy"):
                                kkyy = parsed.get("kkyy")[0]
                            if parsed.get("feedit"):
                                feededit = parsed.get("feedit")[0]
                            if parsed.get("k"):
                                k = parsed.get("k")[0]
                            if parsed.get("key"):
                                key = parsed.get("key")[0]
                            if parsed.get("pageid"):
                                pageid = parsed.get("pageid")[0]
                            if parsed.get("version"):
                                version = parsed.get("version")[0]
                            if parsed.get("agent"):
                                agent = parsed.get("agent")[0]
                            if parsed.get("category"):
                                category = parsed.get("category")[0]
                            if parsed.get("c"):
                                c = parsed.get("c")[0]
                        except Exception as e3:
                            logger.warning(f"Raw body parsing also failed: {e3}")
        except Exception as e:
            logger.warning(f"Body parsing failed: {e}")
    
    # Log POST variables for debugging
    if log_post_variables:
        try:
            # Get URL
            url = str(request.url)
            
            # Get query params as dict
            query_params_dict = dict(request.query_params)
            
            # Convert form_data to dict if it's a Form object
            form_data_dict = None
            if form_data:
                try:
                    form_data_dict = dict(form_data)
                except Exception:
                    form_data_dict = None
            
            # Get raw body as string if form_data and json_data are both None
            raw_body_str = None
            if not form_data_dict and not json_data and raw_body:
                try:
                    raw_body_str = raw_body.decode('utf-8')
                except Exception:
                    raw_body_str = None
            
            # Get headers
            headers_dict = dict(request.headers)
            
            # Call logging function
            log_post_variables(
                endpoint="Article.php",
                method=request.method,
                url=url,
                query_params=query_params_dict,
                form_data=form_data_dict,
                json_data=json_data,
                raw_body=raw_body_str,
                headers=headers_dict
            )
        except Exception as e:
            # Don't let logging errors break the endpoint
            logger.warning(f"Failed to log POST variables: {e}")
    
    # WordPress plugin feed routing (kkyy-based)
    if apiid and apikey and kkyy:
        # Normalize kkyy - handle URL encoding (e.g., %27 for ')
        from urllib.parse import unquote
        kkyy_normalized = unquote(str(kkyy)).strip("'\"")
        
        # Debug logging for parameter extraction
        logger.info(f"WordPress plugin feed routing: apiid={apiid}, apikey={apikey[:10]}..., kkyy={kkyy}, kkyy_normalized={kkyy_normalized}")
        
        # Route to WordPress plugin feeds based on kkyy value
        if kkyy_normalized == 'AKhpU6QAbMtUDTphRPCezo96CztR9EXR' or kkyy_normalized == '1u1FHacsrHy6jR5ztB6tWfzm30hDPL':
            # Route to apifeedwp30 handler
            # Get feededit from query params, form data, or JSON (PHP $_REQUEST gets both)
            feededit_param = feededit or request.query_params.get('feedit')
            if not feededit_param:
                if form_data:
                    feededit_param = form_data.get('feedit')
                elif json_data:
                    feededit_param = json_data.get('feedit')
            serveup_param = request.query_params.get('serveup', '0')
            if form_data:
                serveup_param = form_data.get('serveup', serveup_param)
            elif json_data:
                serveup_param = json_data.get('serveup', serveup_param)
            return await handle_apifeedwp30(
                domain=domain,
                apiid=apiid,
                apikey=apikey,
                kkyy=kkyy_normalized,  # Use normalized kkyy
                request=request,
                form_data=form_data,
                json_data=json_data,
                feededit=feededit_param,
                serveup=serveup_param
            )
        # Add other kkyy routing as needed
        elif kkyy_normalized == 'Nq8dVL6XRTpvmySOVdQLLuxcZpIOp45z94':
            # Route to apifeedwp6.1
            feededit_param = feededit or request.query_params.get('feedit')
            if not feededit_param:
                if form_data:
                    feededit_param = form_data.get('feedit')
                elif json_data:
                    feededit_param = json_data.get('feedit')
            return await handle_apifeedwp61(
                domain=domain,
                request=request,
                form_data=form_data,
                json_data=json_data,
                feededit=feededit_param,
                kkyy=kkyy_normalized
            )
        elif kkyy_normalized == 'AFfa0fd7KMD98enfawrut7cySa15yV7BXpS85':
            # Route to apifeedwp5.9
            logger.info(f"Matched kkyy for apifeedwp5.9: {kkyy_normalized}, feededit={feedit}")
            # #region agent log
            try:
                with open(r"c:\Users\seowe\Saved Games\frl-python-api\.cursor\debug.log", "a", encoding="utf-8") as f:
                    import json, time
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"article.py:337","message":"Before calling handle_apifeedwp59","data":{"kkyy":kkyy_normalized,"feededit":str(feededit),"domain":str(domain)},"timestamp":int(time.time()*1000)})+"\n")
                    f.flush()
            except: pass
            # #endregion
            feededit_param = feededit or request.query_params.get('feedit')
            if not feededit_param:
                if form_data:
                    feededit_param = form_data.get('feedit')
                elif json_data:
                    feededit_param = json_data.get('feedit')
            logger.info(f"Calling handle_apifeedwp59 with feededit={feededit_param}, domain={domain}")
            return await handle_apifeedwp59(
                domain=domain,
                request=request,
                form_data=form_data,
                json_data=json_data,
                feededit=feededit_param,
                kkyy=kkyy_normalized
            )
        elif kkyy_normalized == 'KVFotrmIERNortemkl39jwetsdakfhklo8wer7':
            # Route to apifeedwp6
            logger.info(f"Matched kkyy for apifeedwp6: {kkyy_normalized}")
            pass
        else:
            # Unknown kkyy value - return error instead of falling through to standard routing
            logger.warning(f"Unknown kkyy value: {kkyy_normalized} (original: {kkyy})")
            return JSONResponse(
                content={"error": "Invalid kkyy parameter", "kkyy": kkyy_normalized},
                status_code=400
            )
    
    # Standard Article.php routing (without API auth)
    if not domain:
        raise HTTPException(status_code=400, detail="Domain parameter required")
    
    # Validate domain exists
    domain_data = db.fetch_row(
        "SELECT id FROM bwp_domains WHERE domain_name = %s AND deleted != 1",
        (domain,)
    )
    
    if not domain_data:
        raise HTTPException(status_code=404, detail="Invalid domain")
    
    domainid = domain_data['id']
    
    # Route based on Action parameter
    if not Action:
        Action = ''
    
    # Handle CheckFiles endpoint (case-insensitive) - public health check
    if Action and isinstance(Action, str) and Action.lower() == "checkfiles":
        return PlainTextResponse(content="FRL CheckFiles OK")
    
    # Get full domain data for Action handlers
    domain_full_sql = """
        SELECT d.*, s.servicetype, s.keywords as service_keywords, d.script_version, d.wp_plugin
        FROM bwp_domains d
        LEFT JOIN bwp_services s ON d.servicetype = s.id
        WHERE d.id = %s AND d.deleted != 1
    """
    domain_category = db.fetch_row(domain_full_sql, (domainid,))
    
    if not domain_category:
        raise HTTPException(status_code=404, detail="Domain not found")
    
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
    
    # Handle WordPress plugin actions (when wp_plugin=1 and script_version >= 5)
    # Convert script_version to float for comparison (handles '5.0', '5.0.x', etc.)
    script_version_str = domain_category.get('script_version', '0') or '0'
    try:
        # Extract numeric part (e.g., '5.0.x' -> 5.0, '5' -> 5.0)
        if isinstance(script_version_str, str):
            parts = script_version_str.split('.')
            script_version = float(parts[0] + '.' + parts[1] if len(parts) > 1 else parts[0])
        else:
            script_version = float(script_version_str)
    except (ValueError, IndexError, TypeError):
        script_version = 0.0
    
    wp_plugin = domain_category.get('wp_plugin') or 0
    if wp_plugin == 1 and script_version >= 5:
        # Extract pageid from slug if needed
        pageid_param = pageid or ''
        keyword_param = k or key or ''
        
        # Parse pageid from slug format (keyword-pageid or keyword-pageidbc or keyword-pageiddc)
        bubbleid = None
        if pageid_param:
            try:
                bubbleid = int(pageid_param)
            except ValueError:
                # Try to extract from slug
                if 'bc' in pageid_param:
                    bubbleid = int(pageid_param.replace('bc', ''))
                elif 'dc' in pageid_param:
                    bubbleid = int(pageid_param.replace('dc', ''))
                else:
                    bubbleid = int(pageid_param)
        
        if Action == '1':
            # Website Reference page
            from app.services.content import build_page_wp, get_header_footer, build_metaheader, wrap_content_with_header_footer
            wpage = build_page_wp(
                bubbleid=bubbleid,
                domainid=domainid,
                agent=agent or '',
                keyword=keyword_param,
                domain_data=domain_category,
                domain_settings=domain_settings
            )
            
            # For WordPress plugin, don't add header/footer (WordPress handles it)
            if wp_plugin == 1:
                return HTMLResponse(content=wpage)
            
            # For non-WP, get header/footer and wrap content
            header_footer_data = get_header_footer(domainid, domain_category.get('status'), keyword_param)
            
            # Get bubble data for metaheader
            bubble_sql = """
                SELECT b.*, c.category AS bubblecat, c.bubblefeedid AS bubblecatid, c.id AS bubblecatsid 
                FROM bwp_bubblefeed b 
                LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid 
                WHERE b.domainid = %s AND b.id = %s
            """
            bubble = db.fetch_row(bubble_sql, (domainid, bubbleid)) if bubbleid else None
            
            # Build canonical URL
            if domain_settings.get('usedurl') == 1 and domain_category.get('domain_url'):
                linkdomain = domain_category['domain_url'].rstrip('/')
            else:
                if domain_category.get('ishttps') == 1:
                    linkdomain = 'https://'
                else:
                    linkdomain = 'http://'
                if domain_category.get('usewww') == 1:
                    linkdomain += 'www.' + domain_category['domain_name']
                else:
                    linkdomain += domain_category['domain_name']
            
            canonical_url = linkdomain + '/' + keyword_param.lower().replace(' ', '-') + '-' + str(bubbleid) + '/' if bubbleid else linkdomain
            
            # Build metaheader
            metaheader = build_metaheader(
                domainid=domainid,
                domain_data=domain_category,
                domain_settings=domain_settings,
                action='1',
                keyword=keyword_param,
                pageid=bubbleid or 0,
                bubble=bubble
            )
            
            # Wrap content with header/footer
            full_page = wrap_content_with_header_footer(
                content=wpage,
                header=header_footer_data['header'],
                footer=header_footer_data['footer'],
                metaheader=metaheader,
                canonical_url=canonical_url,
                wp_plugin=wp_plugin
            )
            
            return HTMLResponse(content=full_page)
        
        elif Action == '2':
            # Business Collective page
            from app.services.content import build_bcpage_wp, get_header_footer, build_metaheader, wrap_content_with_header_footer
            wpage = build_bcpage_wp(
                bubbleid=bubbleid,
                domainid=domainid,
                agent=agent or '',
                domain_data=domain_category,
                domain_settings=domain_settings
            )
            
            # For WordPress plugin, don't add header/footer (WordPress handles it)
            if wp_plugin == 1:
                return HTMLResponse(content=wpage)
            
            # For non-WP, get header/footer and wrap content
            header_footer_data = get_header_footer(domainid, domain_category.get('status'))
            
            # Get bubble data for metaheader
            bubble_sql = """
                SELECT b.*, c.category AS bubblecat, c.bubblefeedid AS bubblecatid, c.id AS bubblecatsid 
                FROM bwp_bubblefeed b 
                LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid 
                WHERE b.domainid = %s AND b.id = %s
            """
            bubble = db.fetch_row(bubble_sql, (domainid, bubbleid)) if bubbleid else None
            
            # Build canonical URL
            if domain_settings.get('usedurl') == 1 and domain_category.get('domain_url'):
                linkdomain = domain_category['domain_url'].rstrip('/')
            else:
                if domain_category.get('ishttps') == 1:
                    linkdomain = 'https://'
                else:
                    linkdomain = 'http://'
                if domain_category.get('usewww') == 1:
                    linkdomain += 'www.' + domain_category['domain_name']
                else:
                    linkdomain += domain_category['domain_name']
            
            canonical_url = linkdomain + '/?Action=2&k=' + (keyword_param or '').lower().replace(' ', '-') if keyword_param else linkdomain
            
            # Build metaheader
            metaheader = build_metaheader(
                domainid=domainid,
                domain_data=domain_category,
                domain_settings=domain_settings,
                action='2',
                keyword=keyword_param or '',
                pageid=bubbleid or 0,
                bubble=bubble
            )
            
            # Wrap content with header/footer
            full_page = wrap_content_with_header_footer(
                content=wpage,
                header=header_footer_data['header'],
                footer=header_footer_data['footer'],
                metaheader=metaheader,
                canonical_url=canonical_url,
                wp_plugin=wp_plugin
            )
            
            return HTMLResponse(content=full_page)
        
        elif Action == '3':
            # Bubba page
            from app.services.content import build_bubba_page_wp
            wpage = build_bubba_page_wp(
                bubbleid=bubbleid,
                domainid=domainid,
                agent=agent or '',
                keyword=keyword_param,
                domain_data=domain_category,
                domain_settings=domain_settings
            )
            return HTMLResponse(content=wpage)
    
    # Handle other actions (non-WP plugin)
    if Action == '1':
        # Website Reference (non-WP) - use same function as WP but it handles wp_plugin internally
        from app.services.content import (
            build_page_wp, get_header_footer, build_metaheader, wrap_content_with_header_footer,
            code_url, seo_slug, seo_filter_text_custom, clean_title, build_article_links
        )
        import html
        
        # Extract pageid and keyword
        pageid_param = pageid or ''
        keyword_param = k or key or ''
        
        # Parse pageid
        bubbleid = None
        if pageid_param:
            try:
                bubbleid = int(pageid_param)
            except ValueError:
                bubbleid = None
        
        # Check if we should show keyword listing page
        # Show listing if both k and PageID are empty/None OR if the record is not found in database
        show_keyword_listing = False
        
        if not keyword_param and not bubbleid:
            # Both are empty - show listing
            show_keyword_listing = True
        else:
            # Check if the record exists in the database
            if bubbleid:
                # Check by PageID
                bubble_check_sql = """
                    SELECT id FROM bwp_bubblefeed 
                    WHERE domainid = %s AND id = %s AND active = 1 AND deleted != 1
                """
                bubble_check = db.fetch_row(bubble_check_sql, (domainid, bubbleid))
                if not bubble_check:
                    show_keyword_listing = True
            elif keyword_param:
                # Check by keyword - handle both slug format (hyphens) and space format
                keyword_param_lower = keyword_param.lower().strip()
                keyword_param_for_matching = keyword_param_lower.replace('-', ' ')
                
                # Try matching with spaces first (database format)
                keyword_check_sql = """
                    SELECT id FROM bwp_bubblefeed 
                    WHERE domainid = %s AND LOWER(restitle) = %s AND active = 1 AND deleted != 1
                """
                keyword_check = db.fetch_row(keyword_check_sql, (domainid, keyword_param_for_matching))
                
                # If not found, try with original format (might be stored as slug)
                if not keyword_check:
                    keyword_check = db.fetch_row(keyword_check_sql, (domainid, keyword_param_lower))
                
                if not keyword_check:
                    show_keyword_listing = True
        
        # Generate keyword listing page if needed
        if show_keyword_listing:
            # Query for all active main keywords
            keywords_sql = """
                SELECT id, restitle, resshorttext 
                FROM bwp_bubblefeed 
                WHERE domainid = %s AND active = 1 AND deleted != 1 
                ORDER BY restitle ASC
            """
            keywords_list = db.fetch_all(keywords_sql, (domainid,))
            
            # Build keyword listing HTML
            listing_content = ''
            if keywords_list:
                # Build base URL using code_url
                base_url = code_url(domainid, domain_category, domain_settings)
                
                for keyword_entry in keywords_list:
                    keyword_id = keyword_entry.get('id')
                    keyword_title = keyword_entry.get('restitle', '')
                    keyword_shorttext = keyword_entry.get('resshorttext', '')
                    
                    if keyword_title:
                        # Build the main content page URL
                        keyword_slug = seo_slug(seo_filter_text_custom(keyword_title))
                        keyword_url = f"{base_url}?Action=1&k={keyword_slug}&PageID={keyword_id}"
                        
                        # Create h2 with link
                        clean_keyword_title = clean_title(seo_filter_text_custom(keyword_title))
                        listing_content += f'<h2><a href="{keyword_url}">{clean_keyword_title}</a></h2>\n'
                        
                        # Add shorttext in p tag if available
                        if keyword_shorttext:
                            # HTML unescape and filter the shorttext
                            shorttext_cleaned = html.unescape(str(keyword_shorttext))
                            shorttext_cleaned = seo_filter_text_custom(shorttext_cleaned)
                            listing_content += f'<p>{shorttext_cleaned}</p>\n'
            else:
                listing_content = '<p>No keywords found for this domain.</p>'
            
            # Add footer links at the end
            article_links_html = build_article_links(
                pageid=0,
                domainid=domainid,
                domain_data=domain_category,
                domain_settings=domain_settings,
                domain_category=domain_category
            )
            listing_content += article_links_html
            
            # Get header/footer
            header_footer_data = get_header_footer(domainid, domain_category.get('status'), '')
            
            # Build canonical URL
            if domain_settings.get('usedurl') == 1 and domain_category.get('domain_url'):
                linkdomain = domain_category['domain_url'].rstrip('/')
            else:
                if domain_category.get('ishttps') == 1:
                    linkdomain = 'https://'
                else:
                    linkdomain = 'http://'
                if domain_category.get('usewww') == 1:
                    linkdomain += 'www.' + domain_category['domain_name']
                else:
                    linkdomain += domain_category['domain_name']
            
            canonical_url = linkdomain + '/?Action=1'
            
            # Build metaheader (no specific keyword)
            metaheader = build_metaheader(
                domainid=domainid,
                domain_data=domain_category,
                domain_settings=domain_settings,
                action='1',
                keyword='',
                pageid=0,
                bubble=None
            )
            
            # Wrap content with header/footer
            full_page = wrap_content_with_header_footer(
                content=listing_content,
                header=header_footer_data['header'],
                footer=header_footer_data['footer'],
                metaheader=metaheader,
                canonical_url=canonical_url,
                wp_plugin=wp_plugin
            )
            
            return HTMLResponse(content=full_page)
        
        # Continue with normal single keyword page handling
        wpage = build_page_wp(
            bubbleid=bubbleid,
            domainid=domainid,
            agent=agent or '',
            keyword=keyword_param,
            domain_data=domain_category,
            domain_settings=domain_settings
        )
        
        # Get header/footer and wrap content (non-WP always uses header/footer)
        header_footer_data = get_header_footer(domainid, domain_category.get('status'), keyword_param)
        
        # Get bubble data for metaheader
        bubble_sql = """
            SELECT b.*, c.category AS bubblecat, c.bubblefeedid AS bubblecatid, c.id AS bubblecatsid 
            FROM bwp_bubblefeed b 
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid 
            WHERE b.domainid = %s AND b.id = %s
        """
        bubble = db.fetch_row(bubble_sql, (domainid, bubbleid)) if bubbleid else None
        
        # Build canonical URL
        if domain_settings.get('usedurl') == 1 and domain_category.get('domain_url'):
            linkdomain = domain_category['domain_url'].rstrip('/')
        else:
            if domain_category.get('ishttps') == 1:
                linkdomain = 'https://'
            else:
                linkdomain = 'http://'
            if domain_category.get('usewww') == 1:
                linkdomain += 'www.' + domain_category['domain_name']
            else:
                linkdomain += domain_category['domain_name']
        
        canonical_url = linkdomain + '/?Action=1&k=' + keyword_param.lower().replace(' ', '-') + ('&PageID=' + str(bubbleid) if bubbleid else '') if keyword_param else linkdomain
        
        # Build metaheader
        metaheader = build_metaheader(
            domainid=domainid,
            domain_data=domain_category,
            domain_settings=domain_settings,
            action='1',
            keyword=keyword_param,
            pageid=bubbleid or 0,
            bubble=bubble
        )
        
        # Wrap content with header/footer
        full_page = wrap_content_with_header_footer(
            content=wpage,
            header=header_footer_data['header'],
            footer=header_footer_data['footer'],
            metaheader=metaheader,
            canonical_url=canonical_url,
            wp_plugin=wp_plugin
        )
        
        return HTMLResponse(content=full_page)
    elif Action == '2':
        # Business Collective (non-WP) - use same function as WP but it handles wp_plugin internally
        from app.services.content import build_bcpage_wp, get_header_footer, build_metaheader, wrap_content_with_header_footer, get_domain_keywords_from_bubblefeed
        from fastapi.responses import RedirectResponse
        
        # PHP businesscollective.php lines 10-15: Redirect if category is set
        # Use category or c parameter
        category_param = category or c
        if category_param:
            # Build redirect URL to Action=1
            if domain_settings.get('usedurl') == 1 and domain_category.get('domain_url'):
                linkdomain = domain_category['domain_url'].rstrip('/')
            else:
                if domain_category.get('ishttps') == 1:
                    linkdomain = 'https://'
                else:
                    linkdomain = 'http://'
                if domain_category.get('usewww') == 1:
                    linkdomain += 'www.' + domain_category['domain_name']
                else:
                    linkdomain += domain_category['domain_name']
            
            keyword_param = k or key or ''
            pageid_param = pageid or ''
            redirect_url = f"{linkdomain}/?Action=1&k={keyword_param.replace(' ', '-')}"
            if pageid_param:
                redirect_url += f"&PageID={pageid_param}"
            return HTMLResponse(content=f'<script>document.location=\'{redirect_url}\';</script><noscript><div style="text-align:center;">404 - Page does not exist</div>')
        
        # PHP businesscollective.php lines 64-109: Keyword matching logic
        pageid_param = pageid or ''
        keyword_param_orig = k or key or ''
        keyword_param = keyword_param_orig.lower().strip() if keyword_param_orig else ''
        
        # Convert slug format (hyphens) to keyword format (spaces) for matching
        # The k parameter might be in slug format (hvac-culver-city) but keywords are stored with spaces
        keyword_param_for_matching = keyword_param.replace('-', ' ') if keyword_param else ''
        
        # Get domain keywords from bubblefeed (PHP DomainKeywordsStr)
        keywords = get_domain_keywords_from_bubblefeed(domainid, displayorder=0)
        
        # Get altkeywords from domain
        altkeywords_str = domain_category.get('altkeywords', '') or ''
        if altkeywords_str:
            altkeywords = [k.strip().lower() for k in altkeywords_str.split(',') if k.strip()]
            keywords = keywords + altkeywords
        
        # Remove duplicates and sort (PHP lines 69-72)
        keywords = list(dict.fromkeys(keywords))  # Preserves order while removing duplicates
        keywords.sort()
        
        # Match keyword (PHP lines 75-83)
        # Try matching both the original parameter and the converted version
        key_index = None
        usefirstkeyword = False
        if keyword_param_for_matching:
            try:
                # First try the converted version (spaces)
                key_index = keywords.index(keyword_param_for_matching)
                keyword_param = keyword_param_for_matching
            except ValueError:
                try:
                    # If that fails, try the original (might be stored as slug)
                    key_index = keywords.index(keyword_param)
                except ValueError:
                    key_index = None
        
        if key_index is None:
            if keywords:
                keyword_param = keywords[0]
                key_index = 0
                usefirstkeyword = True
            else:
                # No keywords found - return error or default
                return HTMLResponse(content="No keywords found for this domain", status_code=404)
        
        # Get bubblefeed record for matched keyword (PHP lines 85-109)
        bubbleid = None
        res_sql = """
            SELECT b.id, b.restitle, b.resfulltext, b.resshorttext, b.resfeedtext,
                   IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category
            FROM bwp_bubblefeed b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
            WHERE b.domainid = %s AND b.deleted != 1 AND b.restitle = %s
        """
        res = db.fetch_row(res_sql, (domainid, keyword_param))
        
        # If no record found, get first bubblefeed with links (PHP lines 94-109)
        if not res:
            res_sql = """
                SELECT b.*
                FROM bwp_bubblefeed b
                LEFT JOIN bwp_link_placement l ON l.showondomainid = %s AND l.deleted != 1
                WHERE b.domainid = %s
                AND b.id = l.showonpgid
                AND b.deleted != 1
                ORDER BY b.createdDate
                LIMIT 1
            """
            res = db.fetch_row(res_sql, (domainid, domainid))
            if res:
                keyword_param = res.get('restitle', '')
                key_index = 0
                usefirstkeyword = True
        
        if not res:
            return HTMLResponse(content="No valid keyword found for this domain", status_code=404)
        
        bubbleid = res.get('id')
        keyword_param = res.get('restitle', keyword_param)
        
        # PHP lines 199-203: Redirect if keyword doesn't match and original was provided
        if (key_index is None or usefirstkeyword) and keyword_param_orig:
            # Redirect to Action=2 without keyword
            if domain_settings.get('usedurl') == 1 and domain_category.get('domain_url'):
                linkdomain = domain_category['domain_url'].rstrip('/')
            else:
                if domain_category.get('ishttps') == 1:
                    linkdomain = 'https://'
                else:
                    linkdomain = 'http://'
                if domain_category.get('usewww') == 1:
                    linkdomain += 'www.' + domain_category['domain_name']
                else:
                    linkdomain += domain_category['domain_name']
            
            redirect_url = f"{linkdomain}/?Action=2"
            return HTMLResponse(content=f'<meta http-equiv="refresh" content="0;URL={redirect_url}">')
        
        wpage = build_bcpage_wp(
            bubbleid=bubbleid,
            domainid=domainid,
            agent=agent or '',
            domain_data=domain_category,
            domain_settings=domain_settings
        )
        
        # Get header/footer and wrap content (non-WP always uses header/footer)
        header_footer_data = get_header_footer(domainid, domain_category.get('status'), keyword_param)
        
        # Get bubble data for metaheader
        bubble_sql = """
            SELECT b.*, c.category AS bubblecat, c.bubblefeedid AS bubblecatid, c.id AS bubblecatsid 
            FROM bwp_bubblefeed b 
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid 
            WHERE b.domainid = %s AND b.id = %s
        """
        bubble = db.fetch_row(bubble_sql, (domainid, bubbleid)) if bubbleid else None
        
        # Build canonical URL
        if domain_settings.get('usedurl') == 1 and domain_category.get('domain_url'):
            linkdomain = domain_category['domain_url'].rstrip('/')
        else:
            if domain_category.get('ishttps') == 1:
                linkdomain = 'https://'
            else:
                linkdomain = 'http://'
            if domain_category.get('usewww') == 1:
                linkdomain += 'www.' + domain_category['domain_name']
            else:
                linkdomain += domain_category['domain_name']
        
        canonical_url = linkdomain + '/?Action=2&k=' + keyword_param.lower().replace(' ', '-') if keyword_param else linkdomain
        
        # Build metaheader
        metaheader = build_metaheader(
            domainid=domainid,
            domain_data=domain_category,
            domain_settings=domain_settings,
            action='2',
            keyword=keyword_param or '',
            pageid=bubbleid or 0,
            bubble=bubble
        )
        
        # Wrap content with header/footer
        full_page = wrap_content_with_header_footer(
            content=wpage,
            header=header_footer_data['header'],
            footer=header_footer_data['footer'],
            metaheader=metaheader,
            canonical_url=canonical_url,
            wp_plugin=wp_plugin
        )
        
        return HTMLResponse(content=full_page)
    # ... other actions
    
    return {"message": "Endpoint not yet implemented", "domain": domain, "action": Action}


async def handle_apifeedwp30(
    request: Request,
    domain: Optional[str],
    apiid: str,
    apikey: str,
    kkyy: str,
    feededit: Optional[str],
    serveup: Optional[str] = None,
    form_data: Optional[dict] = None,
    json_data: Optional[dict] = None
):
    """
    Handle apifeedwp30.php requests (WordPress 3.0+ plugin feed).
    """
    
    # Validate API credentials
    if not domain:
        return JSONResponse(content={"error": "Domain parameter required"}, status_code=400)
    
    userid = validate_api_credentials(apiid, apikey)
    if not userid:
        return JSONResponse(content={"error": "Invalid API credentials"}, status_code=401)
    
    # Get domain data
    sql = """
        SELECT d.id as domainid, d.domain_name, d.servicetype, d.writerlock, d.domainip, 
               d.showsnapshot, d.wr_address, d.userid, d.status, d.wr_video, d.wr_facebook, 
               d.wr_googleplus, d.wr_twitter, d.wr_yelp, d.wr_bing, d.wr_name, d.wr_phone, 
               d.linkexchange, d.resourcesactive, d.template_file, d.wp_plugin, 
               r.email as owneremail, s.price
        FROM bwp_domains d
        LEFT JOIN bwp_register r ON d.userid = r.id
        LEFT JOIN bwp_services s ON d.servicetype = s.id
        WHERE d.domain_name = %s AND d.deleted != 1
    """
    
    domains = db.fetch_all(sql, (domain,))
    
    if not domains:
        return JSONResponse(content={"error": "Invalid domain"}, status_code=404)
    
    domain_data = domains[0]
    domainid = domain_data['domainid']
    
    # Get domain settings
    domain_settings = db.fetch_row(
        "SELECT * FROM bwp_domain_settings WHERE domainid = %s",
        (domainid,)
    )
    
    if not domain_settings:
        # Create default settings
        db.execute(
            "INSERT INTO bwp_domain_settings SET domainid = %s",
            (domainid,)
        )
        domain_settings = db.fetch_row(
            "SELECT * FROM bwp_domain_settings WHERE domainid = %s",
            (domainid,)
        )
    
    # Handle feededit parameter
    if feededit == '2':
        # Generate footer HTML
        footer_html = build_footer_wp(domainid, domain_data, domain_settings)
        
        # Return JSON with footer (matching PHP format)
        # PHP: if serveup: json_encode(array('footer' => htmlentities($return)))
        #      else: json_encode(htmlentities($return))
        import json
        import html
        # HTML escape the footer (like PHP htmlentities)
        escaped_html = html.escape(footer_html)
        
        # Check serveup parameter
        if serveup == '1':
            # Return as object with 'footer' key
            return Response(
                content=json.dumps({'footer': escaped_html}),
                media_type="application/json"
            )
        else:
            # Return as JSON string (default)
            return Response(
                content=json.dumps(escaped_html),
                media_type="application/json"
            )
    
    elif feededit == '1':
        # Handle feededit=1 (pages array)
        # Get agent parameter for content generation
        agent_param = request.query_params.get('agent', '')
        if form_data:
            agent_param = form_data.get('agent', agent_param)
        elif json_data:
            agent_param = json_data.get('agent', agent_param)
        
        # Check serveup parameter - if 1, generate post_content
        serveup_val = serveup if serveup else '0'
        if form_data:
            serveup_val = form_data.get('serveup', serveup_val)
        elif json_data:
            serveup_val = json_data.get('serveup', serveup_val)
        
        pagesarray = build_pages_array(
            domainid=domainid,
            domain_data=domain_data,
            domain_settings=domain_settings,
            template_file=domain_data.get('template_file'),
            serveup=(serveup_val == '1'),
            agent=agent_param
        )
        return JSONResponse(content=pagesarray)
    
    elif feededit == 'add':
        # Handle feededit=add - Returns domain info with cade data, sets wp_plugin=1
        # Get cade_level from domain_settings
        cade_level = domain_settings.get('cade_level', 0)
        if cade_level is None:
            cade_level = 0
        
        # Get service info
        service_sql = "SELECT servicetype, keywords FROM bwp_services WHERE id = %s"
        service = db.fetch_row(service_sql, (domain_data.get('servicetype'),))
        
        if not service:
            return JSONResponse(content={"error": "Service not found"}, status_code=404)
        
        servicetypename = service.get('servicetype', '')
        keywords = int(service.get('keywords', 0))
        
        # Check if SEOM or BRON service type
        from app.services.content import is_seom, is_bron
        if is_seom(domain_data.get('servicetype')) or is_bron(domain_data.get('servicetype')):
            keywords = keywords * 3
        
        # Build response - match PHP structure exactly (all domain fields + cade object)
        rdomains = [{
            'domainid': str(domain_data['domainid']),
            'servicetype': str(domain_data.get('servicetype', '')),
            'domainip': domain_data.get('domainip', ''),
            'showsnapshot': str(domain_data.get('showsnapshot', '0')),
            'wr_address': domain_data.get('wr_address', ''),
            'userid': str(domain_data.get('userid', '')),
            'status': str(domain_data.get('status', '')),
            'wr_video': domain_data.get('wr_video', ''),
            'wr_facebook': domain_data.get('wr_facebook', ''),
            'wr_googleplus': domain_data.get('wr_googleplus', ''),
            'wr_twitter': domain_data.get('wr_twitter', ''),
            'wr_linkedin': domain_data.get('wr_linkedin', ''),
            'wr_name': domain_data.get('wr_name', ''),
            'owneremail': domain_data.get('owneremail', ''),
            'price': str(domain_data.get('price', '')),
            'cade': {
                'level': int(cade_level),
                'keywords': int(keywords),
                'servicetype': servicetypename
            }
        }]
        
        # Update wp_plugin=1, spydermap=0
        db.execute(
            "UPDATE bwp_domains SET wp_plugin=1, spydermap=0 WHERE id = %s",
            (domainid,)
        )
        
        return JSONResponse(content=rdomains)
    
    elif feededit == 'head':
        # Handle feededit=head - Returns head scripts (umami analytics)
        umamiid = domain_settings.get('umamiid')
        
        if umamiid and umamiid.strip():
            return_script = f'<script async src="https://analytics.umami.is/script.js" data-website-id="{umamiid}"></script>'
        else:
            return_script = 'No Scripts'
        
        # Return as JSON-encoded HTML-escaped string
        import json
        import html
        escaped_script = html.escape(return_script)
        return Response(
            content=json.dumps(escaped_script),
            media_type="application/json"
        )
    
    elif feededit == '5':
        # Handle feededit=5 - Deactivate domain (sets wp_plugin=0, spydermap=0)
        db.execute(
            "UPDATE bwp_domains SET wp_plugin=0, spydermap=0 WHERE id = %s",
            (domainid,)
        )
        return Response(content="success", media_type="text/plain")
    
    else:
        # Default: return domain data as JSON
        return JSONResponse(content=domains)


async def handle_apifeedwp61(
    request: Request,
    domain: Optional[str],
    feededit: Optional[str],
    kkyy: str,
    form_data: Optional[dict] = None,
    json_data: Optional[dict] = None
):
    """
    Handle apifeedwp6.1.php requests (WordPress 6.1+ plugin feed).
    """
    
    # Validate domain parameter
    if not domain:
        return PlainTextResponse(content="Invalid Request F105", status_code=400)
    
    # Get domain data
    sql = """
        SELECT d.id as domainid, d.domain_name, d.servicetype, d.writerlock, d.domainip, 
               d.showsnapshot, d.wr_address, d.userid, d.status, d.wr_video, d.wr_facebook, 
               d.wr_googleplus, d.wr_twitter, d.wr_yelp, d.wr_bing, d.wr_name, d.linkexchange, 
               d.resourcesactive, d.template_file, r.email as owneremail, s.price
        FROM bwp_domains d
        LEFT JOIN bwp_register r ON d.userid = r.id
        LEFT JOIN bwp_services s ON d.servicetype = s.id
        WHERE d.domain_name = %s AND d.deleted != 1
    """
    
    domains = db.fetch_all(sql, (domain,))
    
    if not domains:
        return PlainTextResponse(content="Domain Does Not Exist", status_code=404)
    
    domain_data = domains[0]
    domainid = domain_data['domainid']
    
    # Handle feededit parameter
    if feededit == 'add':
        # Update domain with wp_plugin=1, spydermap=0, script_version='6.1'
        db.execute(
            "UPDATE bwp_domains SET wp_plugin=1, spydermap=0, script_version='6.1' WHERE id = %s",
            (domainid,)
        )
        
        # Return limited domain data
        rdomains = [{
            'domainid': domain_data['domainid'],
            'status': domain_data['status'],
            'wr_name': domain_data.get('wr_name', ''),
            'owneremail': domain_data.get('owneremail', '')
        }]
        
        return JSONResponse(content=rdomains)
    
    elif feededit == '1' or feededit == 1:
        # Get template_file from domain
        template_file = domain_data.get('template_file', '')
        
        # Get agent parameter
        agent = request.query_params.get('agent', '')
        if form_data:
            agent = form_data.get('agent', agent)
        elif json_data:
            agent = json_data.get('agent', agent)
        
        pagesarray = []
        import html
        
        # a. Bubblefeed pages (if resourcesactive is true)
        if domain_data.get('resourcesactive'):
            sql = """
                SELECT b.*, c.category AS bubblecat, c.bubblefeedid AS bubblecatid, c.id AS bubblecatsid
                FROM bwp_bubblefeed b
                LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
                WHERE b.active = 1 AND b.domainid = %s AND b.deleted != 1
            """
            page_ex = db.fetch_all(sql, (domainid,))
            
            for page in page_ex:
                pageid = page['id']
                keyword = clean_title(seo_filter_text_custom(page['restitle']))
                
                # Generate meta title and keywords
                if page.get('metatitle') and page['metatitle'].strip():
                    metaTitle = clean_title(seo_filter_text_custom(page['metatitle']))
                    metaKeywords = seo_filter_text_custom(page['restitle']).lower()
                    if page.get('bubblecat'):
                        bubbles_sql = "SELECT restitle FROM bwp_bubblefeed WHERE domainid = %s AND categoryid = %s"
                        bubbles = db.fetch_all(bubbles_sql, (domainid, page.get('categoryid')))
                        for bub in bubbles:
                            if bub['restitle'] != page['restitle']:
                                metaKeywords += ', ' + seo_filter_text_custom(bub['restitle']).lower()
                else:
                    metaTitle = clean_title(seo_filter_text_custom(page['restitle']))
                    metaKeywords = seo_filter_text_custom(page['restitle']).lower()
                    if page.get('bubblecat'):
                        bubbles_sql = "SELECT restitle FROM bwp_bubblefeed WHERE domainid = %s AND categoryid = %s"
                        bubbles = db.fetch_all(bubbles_sql, (domainid, page.get('categoryid')))
                        for bub in bubbles:
                            if bub['restitle'] != page['restitle']:
                                metaTitle += ' - ' + clean_title(seo_filter_text_custom(bub['restitle']))
                                metaKeywords += ', ' + seo_filter_text_custom(bub['restitle']).lower()
                
                # Build excerpt from metadescription or resfulltext
                if page.get('metadescription') and page['metadescription'].strip():
                    sorttext = seo_filter_text_custom(page['metadescription'])
                else:
                    if len(page.get('resfulltext', '')) > 50:
                        # Process resfulltext to match PHP exactly
                        import re
                        content = page.get('resfulltext', '')
                        # PHP order: preg_replace("/\r|\n/", " ", ...), strip_tags, html_entity_decode, seo_filter_text_custom
                        content = re.sub(r'\r|\n', ' ', content)  # Replace newlines with spaces
                        content = re.sub(r'<[^>]+>', '', content)  # Remove HTML tags (strip_tags)
                        content = html.unescape(content)  # html_entity_decode
                        content = seo_filter_text_custom(content)  # seo_filter_text_custom
                        # Then: str_replace('Table of Contents ', '', ...), str_replace('  ', ' ', ...) multiple times
                        content = content.replace('Table of Contents ', '')
                        # Replace multiple spaces (PHP does this multiple times)
                        while '  ' in content:
                            content = content.replace('  ', ' ')
                        content = content.strip()
                        # Split into words and take first 20
                        words = content.split()[:20]
                        sorttext = ' '.join(words) + '... ' + metaTitle
                    else:
                        sorttext = ''
                
                # Create slug: keyword-pageid
                slug_text = seo_filter_text_custom(keyword)
                slug_text = to_ascii(slug_text)
                slug_text = html.unescape(slug_text)
                slug_text = slug_text.lower().replace(' ', '-')
                slug = slug_text + '-' + str(pageid)
                
                # Convert datetime to string if needed
                post_date = page.get('createdDate', '')
                if post_date and hasattr(post_date, 'strftime'):
                    post_date = post_date.strftime('%Y-%m-%d %H:%M:%S')
                elif post_date is None:
                    post_date = ''
                
                pagearray = {
                    'pageid': str(pageid),
                    'post_title': keyword,
                    'canonical': '',
                    'post_type': 'page',
                    'comment_status': 'closed',
                    'ping_status': 'closed',
                    'post_date': str(post_date),
                    'post_excerpt': sorttext,
                    'post_name': slug,
                    'post_status': 'publish',
                    'post_metatitle': metaTitle,
                    'post_metakeywords': metaKeywords,
                    'template_file': template_file
                }
                pagesarray.append(pagearray)
        
        # b. Link placement pages
        sql = """
            SELECT DISTINCT showonpgid
            FROM bwp_link_placement
            WHERE deleted != 1 AND showondomainid = %s
            GROUP BY bubblefeedid
            ORDER BY relevant DESC
        """
        bcpage_ex = db.fetch_all(sql, (domainid,))
        
        for bcpage in bcpage_ex:
            pageid = bcpage['showonpgid']
            bpage = db.fetch_row(
                'SELECT restitle, resshorttext, createdDate FROM bwp_bubblefeed WHERE id = %s',
                (pageid,)
            )
            
            if bpage:
                if len(bpage.get('resshorttext', '')) > 50:
                    sorttext = bpage['resshorttext']
                else:
                    sorttext = ''
                
                keyword = clean_title(seo_filter_text_custom(bpage['restitle']))
                
                # Create slug: keyword-pageid-bc
                slug_text = seo_filter_text_custom(keyword)
                slug_text = to_ascii(slug_text)
                slug_text = html.unescape(slug_text)
                slug_text = slug_text.lower().replace(' ', '-')
                slug = slug_text + '-' + str(pageid) + 'bc'
                
                # Convert datetime to string if needed
                post_date = bpage.get('createdDate', '')
                if post_date and hasattr(post_date, 'strftime'):
                    post_date = post_date.strftime('%Y-%m-%d %H:%M:%S')
                elif post_date is None:
                    post_date = ''
                
                bcpagearray = {
                    'pageid': str(pageid) + 'bc',
                    'post_title': keyword.lower() + ' - ' + domain_data['domain_name'],
                    'post_type': 'page',
                    'comment_status': 'closed',
                    'ping_status': 'closed',
                    'post_date': str(post_date),
                    'post_excerpt': sorttext,
                    'post_name': slug,
                    'post_status': 'publish',
                    'post_metatitle': keyword.lower() + ' - ' + domain_data['domain_name'],
                    'post_metakeywords': keyword.lower() + ', ' + domain_data['domain_name'],
                    'template_file': template_file
                }
                pagesarray.append(bcpagearray)
        
        return JSONResponse(content=pagesarray)
    
    elif feededit == '2' or feededit == 2:
        # Get domain settings
        domain_settings = db.fetch_row(
            "SELECT * FROM bwp_domain_settings WHERE domainid = %s",
            (domainid,)
        )
        
        if not domain_settings:
            # Create default settings
            db.execute(
                "INSERT INTO bwp_domain_settings SET domainid = %s",
                (domainid,)
            )
            domain_settings = db.fetch_row(
                "SELECT * FROM bwp_domain_settings WHERE domainid = %s",
                (domainid,)
            )
        
        # Build footer HTML
        footer_html = build_footer_wp(domainid, domain_data, domain_settings)
        
        # Return footer content as JSON-encoded HTML entities
        import json
        import html
        escaped_html = html.escape(footer_html)
        return Response(
            content=json.dumps(escaped_html),
            media_type="application/json"
        )
    
    else:
        return PlainTextResponse(content="Invalid Request F105", status_code=400)


async def handle_apifeedwp59(
    request: Request,
    domain: Optional[str],
    feededit: Optional[str],
    kkyy: str,
    form_data: Optional[dict] = None,
    json_data: Optional[dict] = None
):
    """
    Handle apifeedwp5.9.php requests (WordPress 5.9 plugin feed).
    """
    try:
        logger.info(f"handle_apifeedwp59 called: domain={domain}, feededit={feedit}, kkyy={kkyy}")
        # #region agent log
        try:
            with open(r"c:\Users\seowe\Saved Games\frl-python-api\.cursor\debug.log", "a", encoding="utf-8") as f:
                import json, time
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"article.py:1453","message":"handle_apifeedwp59 entry","data":{"domain":str(domain),"feededit":str(feededit),"kkyy":str(kkyy)},"timestamp":int(time.time()*1000)})+"\n")
                f.flush()
        except: pass
        # #endregion
        
        # Validate domain parameter
        if not domain:
            return PlainTextResponse(content="Invalid Request F105", status_code=400)
        
        # Get domain data (include contentshare, ishttps, usewww fields)
        sql = """
            SELECT d.id as domainid, d.domain_name, d.servicetype, d.writerlock, d.domainip, 
                   d.showsnapshot, d.wr_address, d.userid, d.status, d.wr_video, d.wr_facebook, 
                   d.wr_googleplus, d.wr_twitter, d.wr_yelp, d.wr_bing, d.wr_name, d.linkexchange, 
                   d.resourcesactive, d.contentshare, d.ishttps, d.usewww, r.email as owneremail, s.price
            FROM bwp_domains d
            LEFT JOIN bwp_register r ON d.userid = r.id
            LEFT JOIN bwp_services s ON d.servicetype = s.id
            WHERE d.domain_name = %s AND d.deleted != 1
        """
        
        domains = db.fetch_all(sql, (domain,))
        # #region agent log
        try:
            with open(r"c:\Users\seowe\Saved Games\frl-python-api\.cursor\debug.log", "a", encoding="utf-8") as f:
                import json, time
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"article.py:1472","message":"After domain query","data":{"domain_count":len(domains) if domains else 0},"timestamp":int(time.time()*1000)})+"\n")
                f.flush()
        except: pass
        # #endregion
        
        if not domains:
            return PlainTextResponse(content="Domain Does Not Exist", status_code=404)
        
        domain_data = domains[0]
        domainid = domain_data['domainid']
        # #region agent log
        try:
            with open(r"c:\Users\seowe\Saved Games\frl-python-api\.cursor\debug.log", "a", encoding="utf-8") as f:
                import json, time
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"article.py:1478","message":"Before feededit handling","data":{"domainid":domainid,"feededit":str(feededit)},"timestamp":int(time.time()*1000)})+"\n")
                f.flush()
        except: pass
        # #endregion
        
        # Handle feededit parameter
        if feededit == 'add':
            try:
                # Update domain with wp_plugin=1, spydermap=0, script_version='5.9'
                db.execute(
                    "UPDATE bwp_domains SET wp_plugin=1, spydermap=0, script_version='5.9' WHERE id = %s",
                    (domainid,)
                )
                
                # Return limited domain data
                rdomains = [{
                    'domainid': domain_data['domainid'],
                    'status': domain_data['status'],
                    'wr_name': domain_data.get('wr_name', ''),
                    'owneremail': domain_data.get('owneremail', '')
                }]
                
                return JSONResponse(content=rdomains)
            except Exception as e:
                logger.error(f"Error in handle_apifeedwp59 feededit=add: {e}")
                logger.error(traceback.format_exc())
                return PlainTextResponse(content="Internal Server Error", status_code=500)
        
        elif feededit == '1' or feededit == 1:
            try:
                logger.info(f"handle_apifeedwp59: Processing feededit=1 for domain={domain}, domainid={domainid}")
                # Get agent parameter
                agent = request.query_params.get('agent', '')
                if form_data:
                    agent = form_data.get('agent', agent)
                elif json_data:
                    agent = json_data.get('agent', agent)
                
                pagesarray = []
                import html
                
                # a. Bubblefeed pages (if resourcesactive is true)
                if domain_data.get('resourcesactive'):
                    sql = """
                        SELECT b.*, c.category AS bubblecat, c.bubblefeedid AS bubblecatid, c.id AS bubblecatsid
                        FROM bwp_bubblefeed b
                        LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
                        WHERE b.active = 1 AND b.domainid = %s AND b.deleted != 1
                    """
                    page_ex = db.fetch_all(sql, (domainid,))
                    
                    for page in page_ex:
                        pageid = page['id']
                        keyword = clean_title(seo_filter_text_custom(page['restitle']))
                        
                        # Generate meta title and keywords (with supporting keywords from same category)
                        if page.get('metatitle') and page['metatitle'].strip():
                            metaTitle = clean_title(seo_filter_text_custom(page['metatitle']))
                            metaKeywords = seo_filter_text_custom(page['restitle']).lower()
                            if page.get('bubblecat'):
                                bubbles_sql = "SELECT restitle FROM bwp_bubblefeed WHERE domainid = %s AND categoryid = %s"
                                bubbles = db.fetch_all(bubbles_sql, (domainid, page.get('categoryid')))
                                for bub in bubbles:
                                    if bub['restitle'] != page['restitle']:
                                        metaKeywords += ', ' + seo_filter_text_custom(bub['restitle']).lower()
                        else:
                            metaTitle = clean_title(seo_filter_text_custom(page['restitle']))
                            metaKeywords = seo_filter_text_custom(page['restitle']).lower()
                            if page.get('bubblecat'):
                                bubbles_sql = "SELECT restitle FROM bwp_bubblefeed WHERE domainid = %s AND categoryid = %s"
                                bubbles = db.fetch_all(bubbles_sql, (domainid, page.get('categoryid')))
                                for bub in bubbles:
                                    if bub['restitle'] != page['restitle']:
                                        metaTitle += ' - ' + clean_title(seo_filter_text_custom(bub['restitle']))
                                        metaKeywords += ', ' + seo_filter_text_custom(bub['restitle']).lower()
                        
                        # Build excerpt from metadescription or resfulltext
                        if page.get('metadescription') and page['metadescription'].strip():
                            sorttext = seo_filter_text_custom(page['metadescription'])
                        else:
                            if len(page.get('resfulltext', '')) > 50:
                                # Process resfulltext to match PHP exactly
                                import re
                                content = page.get('resfulltext', '')
                                # PHP order: strip_tags, html_entity_decode, seo_filter_text_custom
                                content = re.sub(r'<[^>]+>', '', content)  # Remove HTML tags (strip_tags)
                                content = html.unescape(content)  # html_entity_decode
                                content = seo_filter_text_custom(content)  # seo_filter_text_custom
                                # Split into words and take first 20
                                words = content.split()[:20]
                                sorttext = ' '.join(words) + '... ' + metaTitle
                            else:
                                sorttext = ''
                        
                        # Create slug using PHP 5.9 order: toAscii(keyword) → seo_filter_text_custom(...) → html_entity_decode(...) → strtolower(...) → str_replace(' ', '-', ...) → append -pageid
                        slug_text = to_ascii(keyword)  # toAscii first
                        slug_text = seo_filter_text_custom(slug_text)  # seo_filter_text_custom2 (same as seo_filter_text_custom)
                        slug_text = html.unescape(slug_text)  # html_entity_decode
                        slug_text = slug_text.lower().replace(' ', '-')  # strtolower and str_replace
                        slug = slug_text + '-' + str(pageid)
                        
                        # Convert datetime to string if needed
                        post_date = page.get('createdDate', '')
                        if post_date and hasattr(post_date, 'strftime'):
                            post_date = post_date.strftime('%Y-%m-%d %H:%M:%S')
                        elif post_date is None:
                            post_date = ''
                        
                        pagearray = {
                            'pageid': str(pageid),
                            'post_title': keyword,
                            'canonical': '',
                            'post_type': 'page',
                            'comment_status': 'closed',
                            'ping_status': 'closed',
                            'post_date': str(post_date),
                            'post_excerpt': sorttext,
                            'post_name': slug,
                            'post_status': 'publish',
                            'post_metatitle': metaTitle,
                            'post_metakeywords': metaKeywords
                        }
                        pagesarray.append(pagearray)
                
                # b. Link placement pages (if linkexchange == 1)
                if domain_data.get('linkexchange') == 1:
                    sql = """
                        SELECT DISTINCT showonpgid
                        FROM bwp_link_placement
                        WHERE deleted != 1 AND showondomainid = %s
                        GROUP BY bubblefeedid
                        ORDER BY relevant DESC
                    """
                    bcpage_ex = db.fetch_all(sql, (domainid,))
                    
                    for bcpage in bcpage_ex:
                        pageid = bcpage['showonpgid']
                        bpage = db.fetch_row(
                            'SELECT restitle, resshorttext, createdDate FROM bwp_bubblefeed WHERE id = %s',
                            (pageid,)
                        )
                        
                        if bpage:
                            if len(bpage.get('resshorttext', '')) > 50:
                                sorttext = bpage['resshorttext']
                            else:
                                sorttext = ''
                            
                            keyword = clean_title(seo_filter_text_custom(bpage['restitle']))
                            
                            # Create slug using PHP 5.9 order: toAscii(keyword) → seo_filter_text_custom(...) → html_entity_decode(...) → strtolower(...) → str_replace(' ', '-', ...) → append -pageid-bc
                            slug_text = to_ascii(keyword)  # toAscii first
                            slug_text = seo_filter_text_custom(slug_text)  # seo_filter_text_custom2 (same as seo_filter_text_custom)
                            slug_text = html.unescape(slug_text)  # html_entity_decode
                            slug_text = slug_text.lower().replace(' ', '-')  # strtolower and str_replace
                            slug = slug_text + '-' + str(pageid) + 'bc'
                            
                            # Convert datetime to string if needed
                            post_date = bpage.get('createdDate', '')
                            if post_date and hasattr(post_date, 'strftime'):
                                post_date = post_date.strftime('%Y-%m-%d %H:%M:%S')
                            elif post_date is None:
                                post_date = ''
                            
                            bcpagearray = {
                                'pageid': str(pageid) + 'bc',
                                'post_title': keyword.lower() + ' - ' + domain_data['domain_name'],
                                'post_type': 'page',
                                'comment_status': 'closed',
                                'ping_status': 'closed',
                                'post_date': str(post_date),
                                'post_excerpt': sorttext,
                                'post_name': slug,
                                'post_status': 'publish',
                                'post_metatitle': keyword.lower() + ' - ' + domain_data['domain_name'],
                                'post_metakeywords': keyword.lower() + ', ' + domain_data['domain_name']
                            }
                            pagesarray.append(bcpagearray)
                
                return JSONResponse(content=pagesarray)
            except Exception as e:
                logger.error(f"Error in handle_apifeedwp59 feededit=1: {e}")
                logger.error(traceback.format_exc())
                return PlainTextResponse(content="Internal Server Error", status_code=500)
        
        elif feededit == '2' or feededit == 2:
            try:
                # Get domain settings
                domain_settings = db.fetch_row(
                    "SELECT * FROM bwp_domain_settings WHERE domainid = %s",
                    (domainid,)
                )
                
                if not domain_settings:
                    # Create default settings
                    db.execute(
                        "INSERT INTO bwp_domain_settings SET domainid = %s",
                        (domainid,)
                    )
                    domain_settings = db.fetch_row(
                        "SELECT * FROM bwp_domain_settings WHERE domainid = %s",
                        (domainid,)
                    )
                
                # Build footer HTML
                footer_html = build_footer_wp(domainid, domain_data, domain_settings)
                
                # Return footer content as JSON-encoded HTML entities
                import json
                import html
                escaped_html = html.escape(footer_html)
                return Response(
                    content=json.dumps(escaped_html),
                    media_type="application/json"
                )
            except Exception as e:
                logger.error(f"Error in handle_apifeedwp59 feededit=2: {e}")
                logger.error(traceback.format_exc())
                return PlainTextResponse(content="Internal Server Error", status_code=500)
        
        else:
            return PlainTextResponse(content="Invalid Request F105", status_code=400)
    except Exception as e:
        # Top-level error handler to catch any unhandled exceptions
        logger.error(f"Unhandled error in handle_apifeedwp59: {e}")
        logger.error(traceback.format_exc())
        # #region agent log
        try:
            with open(r"c:\Users\seowe\Saved Games\frl-python-api\.cursor\debug.log", "a", encoding="utf-8") as f:
                import json, time
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"article.py:1697","message":"Top-level exception caught","data":{"error":str(e),"error_type":type(e).__name__},"timestamp":int(time.time()*1000)})+"\n")
                f.flush()
        except: pass
        # #endregion
        return PlainTextResponse(content="Internal Server Error", status_code=500)
