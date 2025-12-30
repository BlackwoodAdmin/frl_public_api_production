"""Article.php endpoint - Main content router."""
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, Response
from typing import Optional
import logging
from app.database import db
from app.services.auth import validate_api_credentials
from app.services.content import build_footer_wp

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/Article.php")
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
    """
    
    # WordPress plugin feed routing (kkyy-based)
    if apiid and apikey and kkyy:
        # Route to WordPress plugin feeds based on kkyy value
        if kkyy == 'AKhpU6QAbMtUDTphRPCezo96CztR9EXR' or kkyy == '1u1FHacsrHy6jR5ztB6tWfzm30hDPL':
            # Route to apifeedwp30 handler
            return await handle_apifeedwp30(
                domain=domain,
                apiid=apiid,
                apikey=apikey,
                kkyy=kkyy,
                feededit=feedit,
                debug=debug
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
    
    # Handle different actions
    if Action == '1':
        # Website Reference
        pass
    elif Action == '2':
        # Business Collective
        pass
    # ... other actions
    
    return {"message": "Endpoint not yet implemented", "domain": domain, "action": Action}


async def handle_apifeedwp30(
    domain: Optional[str],
    apiid: str,
    apikey: str,
    kkyy: str,
    feededit: Optional[str],
    debug: str
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
        # PHP: json_encode(htmlentities($return)) when serveup is not set
        # This returns a JSON string containing the HTML-escaped footer
        import json
        import html
        # HTML escape the footer (like PHP htmlentities)
        escaped_html = html.escape(footer_html)
        # Return as JSON string
        return Response(
            content=json.dumps(escaped_html),
            media_type="application/json"
        )
    
    elif feededit == '1':
        # Handle feededit=1 (pages array)
        # TODO: Implement pages array generation
        pass
    
    elif feededit == 'add':
        # Handle feededit=add
        # TODO: Implement add functionality
        pass
    
    else:
        # Default: return domain data as JSON
        return JSONResponse(content=domains)

