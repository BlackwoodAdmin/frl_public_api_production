"""Articles.php endpoint - Homepage/Footer content router."""
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
import logging
from app.database import db
from app.services.content import build_footer_wp, build_page_wp, get_header_footer, build_metaheader, wrap_content_with_header_footer

logger = logging.getLogger(__name__)

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
    debug: Optional[str] = Query("0"),
    nocache: Optional[str] = Query("0"),
):
    """
    Articles.php endpoint - generates homepage/footer content when Action is empty.
    Replicates the PHP Articles.php functionality.
    Handles both GET and POST requests (PHP $_REQUEST gets both).
    """
    
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
        debug = debug or query_params.get("debug", "0")
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
                        debug = debug or json_data.get("debug", "0")
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
                        debug = debug or form_data.get("debug", "0")
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
                                debug = debug or (parsed.get("debug", ["0"])[0])
                                nocache = nocache or (parsed.get("nocache", ["0"])[0])
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Could not parse POST body: {e}")
    
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
    if webworkscms == 1:
        cms_sql = "SELECT * FROM bwp_cms WHERE domainid = %s"
        cms = db.fetch_row(cms_sql, (domainid,))
        
        if cms and cms.get('cmsactive') == 1:
            cmspagetype = cms.get('cmspagetype')
            cmspage = cms.get('cmspage')
            
            if cmspagetype == 1 and cmspage:
                # Get article from bwp_bubblefeed
                article_sql = "SELECT * FROM bwp_bubblefeed WHERE id = %s"
                article = db.fetch_row(article_sql, (cmspage,))
                
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
                        debug=(debug == '1'),
                        agent=agent or '',
                        keyword=article.get('restitle', ''),
                        domain_data=domain_category,
                        domain_settings=domain_settings,
                        artpageid=cmspage,
                        artdomainid=domainid
                    )
                    
                    # Get header and footer
                    header_data = get_header_footer(domainid, domain_category, domain_settings, debug == '1')
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
        
        # TODO: Add social media icons if needed (PHP lines 176-253)
        # For now, just return the footer HTML
        return HTMLResponse(content=footer_html)
    
    # For other cases, return a basic response
    # PHP Articles.php has complex logic for generating homepage content with links, etc.
    # This is a simplified version - full implementation would require more PHP code review
    return HTMLResponse(content="<!-- Articles.php - Action not empty or conditions not met -->")

