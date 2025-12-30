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
    # Add other common parameters as needed
):
    """
    Main Article.php endpoint - routes to different handlers based on parameters.
    Replicates the PHP Article.php functionality.
    Handles both GET and POST requests (PHP $_REQUEST gets both).
    """
    
    # For POST requests, also check form data (PHP $_REQUEST includes both GET and POST)
    form_data = None
    if request.method == "POST":
        try:
            form_data = await request.form()
            # Override query params with form data if present (POST takes precedence like PHP)
            domain = domain or form_data.get("domain")
            Action = Action or form_data.get("Action")
            apiid = apiid or form_data.get("apiid")
            apikey = apikey or form_data.get("apikey")
            kkyy = kkyy or form_data.get("kkyy")
            feededit = feededit or form_data.get("feedit")
            k = k or form_data.get("k")
            key = key or form_data.get("key")
            pageid = pageid or form_data.get("pageid")
            version = version or form_data.get("version", "1.0")
            debug = debug or form_data.get("debug", "0")
            agent = agent or form_data.get("agent")
        except Exception:
            # If form parsing fails, continue with query params only
            pass
    
    # WordPress plugin feed routing (kkyy-based)
    if apiid and apikey and kkyy:
        # Route to WordPress plugin feeds based on kkyy value
        if kkyy == 'AKhpU6QAbMtUDTphRPCezo96CztR9EXR' or kkyy == '1u1FHacsrHy6jR5ztB6tWfzm30hDPL':
            # Route to apifeedwp30 handler
            # Get feededit from query params or form data (PHP $_REQUEST gets both)
            feededit_param = feededit or request.query_params.get('feedit')
            if not feededit_param and form_data:
                feededit_param = form_data.get('feedit')
            serveup_param = request.query_params.get('serveup', '0')
            if form_data:
                serveup_param = form_data.get('serveup', serveup_param)
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
            from app.services.content import build_page_wp
            wpage = build_page_wp(
                bubbleid=bubbleid,
                domainid=domainid,
                debug=debug == '1',
                agent=agent or '',
                keyword=keyword_param,
                domain_data=domain_category,
                domain_settings=domain_settings
            )
            return HTMLResponse(content=wpage)
        
        elif Action == '2':
            # Business Collective page
            from app.services.content import build_bcpage_wp
            wpage = build_bcpage_wp(
                bubbleid=bubbleid,
                domainid=domainid,
                debug=debug == '1',
                agent=agent or '',
                domain_data=domain_category,
                domain_settings=domain_settings
            )
            return HTMLResponse(content=wpage)
        
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
    if Action == '1':
        # Website Reference (non-WP)
        return {"message": "Action=1 (non-WP) not yet implemented", "domain": domain, "action": Action}
    elif Action == '2':
        # Business Collective (non-WP)
        return {"message": "Action=2 (non-WP) not yet implemented", "domain": domain, "action": Action}
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
               d.linkexchange, d.resourcesactive, d.template_file, r.email as owneremail, s.price
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

