"""Article.php endpoint - Main content router."""
from fastapi import APIRouter, Request, Query, HTTPException, Form
from fastapi.responses import JSONResponse, HTMLResponse, Response
from typing import Optional
import logging
from app.database import db
from app.services.auth import validate_api_credentials
from app.services.content import build_footer_wp, build_pages_array

logger = logging.getLogger(__name__)

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
    debug: Optional[str] = Query("0"),
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
    # Initialize these variables for both GET and POST requests
    form_data = None
    json_data = None
    # Initialize feededit_param early to ensure it's always defined
    feededit_param = None
    
    if request.method == "POST":
        # First, check query params (POST requests can have params in URL too)
        # PHP $_REQUEST merges $_GET and $_POST, so we check both
        query_params = dict(request.query_params)
        logger.debug(f"POST request - Query params: {query_params}")
        
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
        debug = debug or query_params.get("debug", "0")
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
        logger.info(f"POST request - Content-Type: {content_type}")
        
        # Read raw body first to see what we're getting
        try:
            raw_body = await request.body()
            logger.info(f"POST request - Raw body length: {len(raw_body)}, body: {raw_body.decode('utf-8', errors='ignore')[:500]}")
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
                    logger.info(f"POST request - JSON data: {json_data}")
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
                    if json_data.get("debug"):
                        debug = json_data.get("debug")
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
                    logger.info(f"POST request - Form data: {form_dict}")
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
                    if form_data.get("debug"):
                        debug = form_data.get("debug")
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
                            logger.info(f"POST request - Parsed from raw body: {parsed}")
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
                            if parsed.get("debug"):
                                debug = parsed.get("debug")[0]
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
        
        logger.debug(f"POST request - Final extracted params - domain: {domain}, apiid: {apiid}, apikey: {apikey}, kkyy: {kkyy}, feededit: {feededit}")
    
    # WordPress plugin feed routing (kkyy-based)
    if apiid and apikey and kkyy:
        # Strip whitespace and quotes from kkyy for comparison (handle URL encoding issues)
        kkyy_clean = kkyy.strip().strip("'\"")
        # Get feededit from query params, form data, or JSON (PHP $_REQUEST gets both)
        # feededit_param was initialized earlier, now update it with actual value
        feededit_param = feededit or request.query_params.get('feedit') or feededit_param
        if not feededit_param:
            if form_data:
                feededit_param = form_data.get('feedit')
            elif json_data:
                feededit_param = json_data.get('feedit')
        logger.debug(f"WordPress plugin routing - kkyy: {repr(kkyy)}, kkyy_clean: {repr(kkyy_clean)}, apiid: {apiid}, apikey: {apikey}, feededit: {feedit_param}")
        # Route to WordPress plugin feeds based on kkyy value
        if kkyy_clean == 'AKhpU6QAbMtUDTphRPCezo96CztR9EXR' or kkyy_clean == '1u1FHacsrHy6jR5ztB6tWfzm30hDPL':
            # Route to apifeedwp30 handler
            # feededit_param already extracted above
            serveup_param = request.query_params.get('serveup', '0')
            if form_data:
                serveup_param = form_data.get('serveup', serveup_param)
            elif json_data:
                serveup_param = json_data.get('serveup', serveup_param)
            return await handle_apifeedwp30(
                domain=domain,
                apiid=apiid,
                apikey=apikey,
                kkyy=kkyy,
                feededit=feededit_param,
                debug=debug,
                serveup=serveup_param
            )
        # Add other kkyy routing as needed
        elif kkyy == 'Nq8dVL6XRTpvmySOVdQLLuxcZpIOp45z94':
            # Route to apifeedwp6.1
            pass
        elif kkyy == 'KVFotrmIERNortemkl39jwetsdakfhklo8wer7':
            # Route to apifeedwp6
            pass
        # ... other kkyy values
    
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
    # #region agent log
    from app.services.content import _debug_log
    _debug_log("article.py:article_endpoint", "Before wp_plugin check", {
        "wp_plugin": wp_plugin,
        "script_version": script_version,
        "script_version_float": script_version,
        "wp_plugin_check": wp_plugin == 1,
        "script_version_check": script_version >= 5,
        "both_conditions": wp_plugin == 1 and script_version >= 5,
        "Action": Action
    }, "A")
    # #endregion
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
        # #region agent log
        _debug_log("article.py:article_endpoint", "After parsing pageid", {
            "pageid_param": pageid_param,
            "bubbleid": bubbleid,
            "keyword_param": keyword_param
        }, "A")
        # #endregion
        
        if Action == '1':
            # Website Reference page
            from app.services.content import build_page_wp, get_header_footer, build_metaheader, wrap_content_with_header_footer, _debug_log, is_bron
            # #region agent log
            _debug_log("article.py:article_endpoint", "Before build_page_wp call", {
                "bubbleid": bubbleid,
                "domainid": domainid,
                "keyword_param": keyword_param,
                "pageid_param": pageid_param,
                "wp_plugin": wp_plugin,
                "script_version": script_version
            }, "A")
            # #endregion
            
            # BRON domains: Skip main keyword pages, but allow supporting keyword pages
            if is_bron(domain_category.get('servicetype')):
                # Check if this is a supporting keyword (exists in bwp_bubblefeedsupport)
                if bubbleid:
                    support_check_sql = """
                        SELECT id FROM bwp_bubblefeedsupport 
                        WHERE id = %s AND domainid = %s AND deleted != 1
                    """
                    is_supporting = db.fetch_row(support_check_sql, (bubbleid, domainid))
                    if not is_supporting:
                        # This is a main keyword for BRON - skip page creation
                        logger.info(f"BRON domain: Skipping main keyword page (bubbleid={bubbleid})")
                        return HTMLResponse(content="", status_code=404)
                elif keyword_param:
                    # Try to find by keyword - check if it's a supporting keyword
                    support_check_sql = """
                        SELECT id FROM bwp_bubblefeedsupport 
                        WHERE restitle = %s AND domainid = %s AND deleted != 1
                    """
                    is_supporting = db.fetch_row(support_check_sql, (keyword_param, domainid))
                    if not is_supporting:
                        # This is a main keyword for BRON - skip page creation
                        logger.info(f"BRON domain: Skipping main keyword page (keyword={keyword_param})")
                        return HTMLResponse(content="", status_code=404)
            
            logger.info(f"WP Plugin Action=1: bubbleid={bubbleid}, domainid={domainid}, keyword={keyword_param}")
            wpage = build_page_wp(
                bubbleid=bubbleid,
                domainid=domainid,
                debug=debug == '1',
                agent=agent or '',
                keyword=keyword_param,
                domain_data=domain_category,
                domain_settings=domain_settings
            )
            # #region agent log
            _debug_log("article.py:article_endpoint", "After build_page_wp call", {
                "wpage_length": len(wpage) if wpage else 0,
                "wpage_empty": not wpage or len(wpage) == 0
            }, "A")
            # #endregion
            logger.info(f"WP Plugin Action=1: wpage length={len(wpage) if wpage else 0}, empty={not wpage or len(wpage) == 0}")
            
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
                debug=debug == '1',
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
                debug=debug == '1',
                agent=agent or '',
                keyword=keyword_param,
                domain_data=domain_category,
                domain_settings=domain_settings
            )
            return HTMLResponse(content=wpage)
    
    # Handle other actions (non-WP plugin)
    # #region agent log
    _debug_log("article.py:article_endpoint", "Non-WP plugin handler", {
        "Action": Action,
        "wp_plugin": wp_plugin,
        "script_version": script_version
    }, "A")
    # #endregion
    if Action == '1':
        # Website Reference (non-WP) - use same function as WP but it handles wp_plugin internally
        from app.services.content import build_page_wp, get_header_footer, build_metaheader, wrap_content_with_header_footer, is_bron
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
        # #region agent log
        _debug_log("article.py:article_endpoint", "Non-WP: Before build_page_wp", {
            "pageid_param": pageid_param,
            "bubbleid": bubbleid,
            "keyword_param": keyword_param
        }, "A")
        # #endregion
        
        # BRON domains: Skip main keyword pages, but allow supporting keyword pages
        if is_bron(domain_category.get('servicetype')):
            # Check if this is a supporting keyword (exists in bwp_bubblefeedsupport)
            if bubbleid:
                support_check_sql = """
                    SELECT id FROM bwp_bubblefeedsupport 
                    WHERE id = %s AND domainid = %s AND deleted != 1
                """
                is_supporting = db.fetch_row(support_check_sql, (bubbleid, domainid))
                if not is_supporting:
                    # This is a main keyword for BRON - skip page creation
                    logger.info(f"BRON domain: Skipping main keyword page (bubbleid={bubbleid})")
                    return HTMLResponse(content="", status_code=404)
            elif keyword_param:
                # Try to find by keyword - check if it's a supporting keyword
                support_check_sql = """
                    SELECT id FROM bwp_bubblefeedsupport 
                    WHERE restitle = %s AND domainid = %s AND deleted != 1
                """
                is_supporting = db.fetch_row(support_check_sql, (keyword_param, domainid))
                if not is_supporting:
                    # This is a main keyword for BRON - skip page creation
                    logger.info(f"BRON domain: Skipping main keyword page (keyword={keyword_param})")
                    return HTMLResponse(content="", status_code=404)
        
        wpage = build_page_wp(
            bubbleid=bubbleid,
            domainid=domainid,
            debug=debug == '1',
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
            debug=debug == '1',
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
    domain: Optional[str],
    apiid: str,
    apikey: str,
    kkyy: str,
    feededit: Optional[str],
    debug: str,
    serveup: Optional[str] = None
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
        pagesarray = build_pages_array(domainid, domain_data, domain_settings, domain_data.get('template_file'))
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
        
        # Build response
        rdomains = [{
            'domainid': domain_data['domainid'],
            'status': domain_data['status'],
            'wr_name': domain_data.get('wr_name', ''),
            'owneremail': domain_data.get('owneremail', ''),
            'servicetype': domain_data.get('servicetype'),
            'cade': {
                'level': cade_level,
                'keywords': keywords,
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

