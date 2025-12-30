"""Content generation services."""
from app.database import db
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def build_footer_wp(domainid: int, domain_data: Dict[str, Any], domain_settings: Dict[str, Any]) -> Dict[str, str]:
    """
    Build footer HTML for WordPress plugin (feedit=2).
    Replicates seo_automation_build_footerWP function from ArticlesWP5.php
    """
    
    # Build link domain
    if domain_settings.get('usedurl') == 1 and domain_data.get('domain_url'):
        linkdomain = domain_data['domain_url'].rstrip('/')
    else:
        if domain_data.get('ishttps') == 1:
            linkdomain = 'https://'
        else:
            linkdomain = 'http://'
        
        if domain_data.get('usewww') == 1:
            linkdomain += 'www.' + domain_data['domain_name']
        else:
            linkdomain += domain_data['domain_name']
    
    # Get keywords
    keywords = get_domain_keywords(domainid)
    keywordcnt = len(keywords)
    
    if keywordcnt == 0:
        keywords = [domain_data['domain_name']]
    
    # Build footer HTML
    foot = ''
    num_lnks = 0
    
    # Get silo pages (bubblefeed entries)
    sql = """
        SELECT b.restitle, b.id, b.linkouturl, c.bubblefeedid, c.category, 
               b.resfulltext, b.resshorttext, b.NoContent,
               (SELECT COUNT(*) FROM bwp_link_placement WHERE showonpgid = b.id AND deleted != 1) AS links_per_page
        FROM bwp_bubblefeed b
        LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != '1'
        WHERE b.domainid = %s AND b.deleted != 1
        ORDER BY b.restitle
    """
    
    silo = db.fetch_all(sql, (domainid,))
    
    if silo:
        foot += '<li>'
        foot += '<ul class="seo-sub-nav">\n'
        
        for item in silo:
            if item.get('id'):
                # Build link
                if item.get('links_per_page', 0) >= 1:
                    # Build Resources link
                    slug = seo_slug(item['restitle']) + '-' + str(item['id']) + 'bc/'
                    bclink = linkdomain + '/' + slug
                    newsf = ' <a style="padding-left: 0px !important;" href="' + bclink + '">Resources</a>'
                else:
                    newsf = ''
                
                    if domain_data.get('resourcesactive') == '1':
                        if (item.get('NoContent') == 0 or is_bron(domain_data.get('servicetype'))) and len(item.get('linkouturl', '').strip()) > 5:
                            # External link
                            foot += '<li><a style="padding-right: 0px !important;" href="' + item['linkouturl'] + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a>' + newsf + '</li>\n'
                        else:
                            # Internal link
                            slug = seo_slug(item['restitle']) + '-' + str(item['id']) + '/'
                            foot += '<li><a style="padding-right: 0px !important;" href="' + linkdomain + '/' + slug + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a>' + newsf + '</li>\n'
                    else:
                        # Business Collective link only
                        slug = seo_slug(item['restitle']) + '-' + str(item['id']) + 'bc/'
                        foot += '<li><a style="padding-right: 0px !important;" href="' + linkdomain + '/' + slug + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a></li>\n'
                
                num_lnks += 1
        
        foot += '</ul>\n'
        foot += 'Articles</li>\n'
    
    # Add Blog and FAQ links if configured
    if domain_settings.get('blogUrl') and len(domain_settings['blogUrl']) > 10:
        foot += '<li><a class="url" style="width: 100%;font-size:12px;line-height:13px;" target="_blank" href="' + domain_settings['blogUrl'] + '">Blog</a></li>\n'
    
    if domain_settings.get('faqUrl') and len(domain_settings['faqUrl']) > 10:
        foot += '<li><a class="url" style="width: 100%;font-size:12px;line-height:13px;" target="_blank" href="' + domain_settings['faqUrl'] + '">FAQ</a></li>\n'
    
    # Build final footer HTML
    if domain_data.get('wr_name'):
        ltest = domain_data['wr_name']
    else:
        ltest = domain_data['domain_name']
    
    foot += '</ul><a href="' + linkdomain + '/"><div class="seo-button-paid">&copy; ' + str(datetime.now().year) + ' ' + ltest + '</div></a></li></ul>\n'
    
    footer_html = '<div class="seo-automation-spacer"></div>\n'
    footer_html += '<div style="display:block !important;" class="seo-footer-section ">\n'
    footer_html += '<ul class="seo-footer-nav num-lite">\n'
    footer_html += '<li>\n'
    footer_html += '<ul>\n'
    footer_html += foot
    footer_html += '<div class="seo-automation-spacer"></div>\n'
    footer_html += '<style>\n'
    footer_html += '.seo-footer-nav li ul li ul {\n'
    footer_html += '\tleft:70px !important;;\n'
    footer_html += '}\n'
    footer_html += '</style>\n'
    footer_html += '</div>'
    
    # Return the footer HTML (will be JSON-encoded and HTML-escaped in the route handler)
    return footer_html


def get_domain_keywords(domainid: int) -> list:
    """Get domain keywords (equivalent to PHP DomainKeywords function)."""
    sql = "SELECT keywords FROM bwp_domains WHERE id = %s"
    result = db.fetch_row(sql, (domainid,))
    if result and result.get('keywords'):
        keywords = [k.strip() for k in result['keywords'].split(',') if k.strip() and k.strip() != 'one way links']
        return keywords
    return []


def seo_filter_text_custom(text: str) -> str:
    """Clean text similar to PHP seo_filter_text_custom."""
    import re
    text = text.strip()
    text = re.sub(r'&(amp;)+', '&', text)
    text = text.replace('&amp;amp;', '&amp;')
    text = text.replace('&amp;mdash;', '&mdash;')
    text = text.replace('&amp;nbsp;', '&nbsp;')
    text = text.replace('&amp;#', '&#')
    text = text.replace("&#39;", "'")
    text = text.replace("&#124;", "|")
    text = text.replace("&gt;", ">")
    text = text.replace("&lt;", "<")
    text = text.replace('&Acirc;', ' ')
    text = text.replace('&acirc;', '')
    text = text.replace('&#128;', '')
    text = text.replace('&#153;', '')
    text = text.replace("&rsquo;", "'")
    text = text.replace("&bull;", " ")
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&ndash;', '-')
    text = text.replace('&ldquo;', '"')
    text = text.replace('&rdquo;', '"')
    text = text.replace('&mdash;', '--')
    return text


def seo_text_custom(text: str) -> str:
    """Clean text similar to PHP seo_text_custom."""
    import re
    text = text.strip()
    text = re.sub(r'&(amp;)+', '&', text)
    text = text.replace("&#39;", "'")
    text = text.replace("&#124;", "|")
    text = text.replace(":", "")
    text = text.replace("'", "")
    return text


def to_ascii(text: str) -> str:
    """Convert text to ASCII (simplified version of PHP toAscii)."""
    import html
    import re
    text = seo_filter_text_custom(text)
    text = text.replace(' &#x26;', '')
    text = html.unescape(text)
    # Basic transliteration (simplified - full version has extensive table)
    text = text.replace("'", "")
    text = text.replace('#039;', '')
    text = text.replace(' & ', ' ')
    text = text.replace('&', '')
    return text


def seo_slug(text: str) -> str:
    """Convert text to SEO-friendly slug."""
    import re
    # Use to_ascii and then convert to slug
    text = to_ascii(text)
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text.strip())
    return text


def clean_title(text: str) -> str:
    """Clean title for display (simplified version of seo_automation_clean_title)."""
    text_lower = text.lower()
    if text.strip() == text_lower.strip():
        # Title case
        return text.strip().title()
    else:
        return text.strip()


def is_bron(servicetype: Optional[int]) -> bool:
    """Check if service type is BRON."""
    if not servicetype:
        return False
    sql = "SELECT * FROM bwp_services WHERE servicetype LIKE 'BRON %%' AND servicetype != 'SEOM 5' AND id = %s"
    result = db.fetch_all(sql, (servicetype,))
    return bool(result)


def is_seom(servicetype: Optional[int]) -> bool:
    """Check if service type is SEOM."""
    if not servicetype:
        return False
    sql = "SELECT * FROM bwp_services WHERE servicetype LIKE 'SEOM %%' AND servicetype != 'SEOM 5' AND id = %s"
    result = db.fetch_all(sql, (servicetype,))
    return bool(result)


def strip_html(text: str) -> str:
    """Strip HTML tags from text."""
    from html.parser import HTMLParser
    class MLStripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self.reset()
            self.strict = False
            self.convert_charrefs = True
            self.fed = []
        def handle_data(self, d):
            self.fed.append(d)
        def get_data(self):
            return ''.join(self.fed)
    s = MLStripper()
    s.feed(text)
    return s.get_data()


def build_excerpt(text: str, max_words: int = 20) -> str:
    """Build excerpt from text (first N words)."""
    if not text or len(text) < 50:
        return ''
    import re
    import html
    # Clean content
    content = re.sub(r'Table of Contents\s+', '', text)
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\r|\n', ' ', content)
    content = html.unescape(content)
    content = seo_filter_text_custom(content)
    content = strip_html(content)
    words = content.split()[:max_words]
    return ' '.join(words) + '... ' if words else ''


def build_pages_array(domainid: int, domain_data: Dict[str, Any], domain_settings: Dict[str, Any], template_file: Optional[str] = None) -> list:
    """
    Build pages array for WordPress plugin (feedit=1).
    Returns array of page objects matching PHP format.
    """
    pagesarray = []
    servicetype = domain_data.get('servicetype')
    
    # 1. Get bubblefeed entries (main pages)
    if domain_data.get('resourcesactive'):
        sql = """
            SELECT b.*, c.category AS bubblecat, c.bubblefeedid AS bubblecatid, c.id AS bubblecatsid
            FROM bwp_bubblefeed b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
            WHERE b.active = 1 AND b.domainid = %s AND b.deleted != 1
        """
        page_ex = db.fetch_all(sql, (domainid,))
        
        for page in page_ex:
            if not is_bron(servicetype) or len(page.get('linkouturl', '')) < 5:
                pageid = page['id']
                keyword = clean_title(seo_filter_text_custom(page['restitle']))
                
                # Build meta title and keywords
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
                    
                    if len(domain_data.get('wr_phone', '')) > 9 and domain_settings.get('phoneintitle') == 1:
                        metaTitle = domain_data['wr_phone'] + ' - ' + metaTitle
                
                # Build excerpt
                if page.get('metadescription') and page['metadescription'].strip():
                    sorttext = seo_filter_text_custom(page['metadescription'])
                    words = sorttext.split()[:20]
                    sorttext = ' '.join(words) + '... '
                else:
                    sorttext = build_excerpt(page.get('resfulltext', ''))
                
                sorttext = strip_html(seo_filter_text_custom(sorttext))
                slug = seo_slug(keyword) + '-' + str(pageid) + '/'
                
                pagearray = {
                    'pageid': str(pageid),
                    'post_title': keyword,
                    'canonical': '',
                    'post_type': 'page',
                    'post_content': '',
                    'comment_status': 'closed',
                    'ping_status': 'closed',
                    'post_date': page.get('createdDate', ''),
                    'post_excerpt': sorttext,
                    'post_name': slug,
                    'post_status': 'publish',
                    'post_metatitle': metaTitle,
                    'post_metakeywords': metaKeywords,
                    'template_file': template_file or ''
                }
                pagesarray.append(pagearray)
    
    # 2. Get bubblefeedsupport entries (support pages) - only for SEOM/BRON
    if is_seom(servicetype) or is_bron(servicetype):
        sql = """
            SELECT ba.id, ba.restitle, ba.resshorttext, ba.resfulltext, ba.createdDate, ba.metatitle, ba.metadescription
            FROM bwp_bubblefeedsupport ba
            LEFT JOIN bwp_bubblefeed bb ON bb.id = ba.bubblefeedid
            WHERE ba.active = 1 AND ba.domainid = %s
            AND CHAR_LENGTH(ba.resfulltext) > 300
            AND bb.active = 1
            AND ba.deleted != 1
            AND bb.deleted != 1
        """
        page_exs = db.fetch_all(sql, (domainid,))
        
        for page in page_exs:
            pageid = page['id']
            keyword = clean_title(seo_filter_text_custom(page['restitle']))
            
            if page.get('metatitle') and page['metatitle'].strip():
                metaTitle = clean_title(seo_filter_text_custom(page['metatitle']))
                metaKeywords = seo_filter_text_custom(page['restitle']).lower()
            else:
                metaTitle = clean_title(seo_filter_text_custom(page['restitle']))
                metaKeywords = seo_filter_text_custom(page['restitle']).lower()
                if len(domain_data.get('wr_phone', '')) > 9 and domain_settings.get('phoneintitle') == 1:
                    metaTitle = domain_data['wr_phone'] + ' - ' + metaTitle
            
            # Build excerpt
            if page.get('metadescription') and page['metadescription'].strip():
                sorttext = seo_filter_text_custom(page['metadescription'])
                words = sorttext.split()[:20]
                sorttext = ' '.join(words) + '... '
            else:
                sorttext = build_excerpt(page.get('resfulltext', ''))
            
            sorttext = strip_html(seo_filter_text_custom(sorttext))
            slug = seo_slug(keyword) + '-' + str(pageid) + '/'
            
            pagearray = {
                'pageid': str(pageid),
                'canonical': '',
                'post_title': keyword,
                'post_type': 'page',
                'post_content': '',
                'comment_status': 'closed',
                'ping_status': 'closed',
                'post_date': page.get('createdDate', ''),
                'post_excerpt': sorttext,
                'post_name': slug,
                'post_status': 'publish',
                'post_metatitle': clean_title(seo_filter_text_custom(metaTitle)),
                'post_metakeywords': seo_filter_text_custom(page['restitle']).lower(),
                'template_file': template_file or ''
            }
            pagesarray.append(pagearray)
    
    # 3. Get business collective pages (bc pages)
    sql = """
        SELECT b.*
        FROM bwp_bubblefeed b
        WHERE b.active = 1 AND b.domainid = %s AND b.deleted != 1
    """
    bcpage_ex = db.fetch_all(sql, (domainid,))
    
    for bcpage in bcpage_ex:
        pageid = bcpage['id']
        if len(bcpage.get('resfeedtext', '')) > 50:
            sorttext = seo_filter_text_custom(bcpage['resfeedtext'])
            import html
            sorttext = html.unescape(sorttext)
            sorttext = strip_html(sorttext)
            words = sorttext.split()[:20]
            sorttext = ' '.join(words) + '... '
        else:
            sorttext = ''
        
        keyword = clean_title(seo_filter_text_custom(bcpage['restitle']))
        
        if is_bron(servicetype):
            slug = str(pageid) + 'bc/'
            metaTitle = domain_data['domain_name'] + ' - ' + str(pageid) + ' - Resources'
            keyword = domain_data['domain_name'] + ' - ' + str(pageid)
        else:
            slug = seo_slug(keyword) + '-' + str(pageid) + 'bc/'
            metaTitle = keyword.lower() + ' - Resources'
        
        sorttext = strip_html(seo_filter_text_custom(sorttext))
        
        if len(domain_data.get('wr_phone', '')) > 9 and domain_settings.get('phoneintitle') == 1:
            metaTitle = domain_data['wr_phone'] + ' - ' + metaTitle
        
        bcpagearray = {
            'pageid': str(pageid) + 'bc',
            'post_title': keyword.lower() + ' - Resources',
            'post_type': 'page',
            'post_content': '',
            'comment_status': 'closed',
            'ping_status': 'closed',
            'post_date': bcpage.get('createdDate', ''),
            'post_excerpt': sorttext,
            'post_name': slug,
            'post_status': 'publish',
            'post_metatitle': metaTitle,
            'post_metakeywords': keyword.lower() + ' Resources',
            'template_file': template_file or ''
        }
        pagesarray.append(bcpagearray)
    
    return pagesarray


def build_page_wp(
    bubbleid: int,
    domainid: int,
    debug: bool,
    agent: str,
    keyword: str,
    domain_data: Dict[str, Any],
    domain_settings: Dict[str, Any],
    artpageid: int = 0,
    artdomainid: int = 0,
    support: int = 0,
    offpageid: int = 0,
    offdomainid: int = 0
) -> str:
    """
    Build Website Reference page HTML (Action=1).
    Replicates seo_automation_build_page from websitereference-wp.php
    
    TODO: Full implementation needed - this is a placeholder
    """
    if not bubbleid or not domainid:
        return ""
    
    # Get bubblefeed data
    sql = """
        SELECT b.id, b.restitle, b.title, b.resfulltext, b.resshorttext, b.linkouturl, 
               b.resphone, b.resvideo, b.resaddress, b.resgooglemaps, b.resname,
               IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category
        FROM bwp_bubblefeed b
        LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
        WHERE b.id = %s AND b.domainid = %s AND b.deleted != 1
    """
    res = db.fetch_row(sql, (bubbleid, domainid))
    
    if not res:
        return ""
    
    # Build basic page HTML (placeholder - needs full implementation)
    wpage = f'<div class="seo-automation-main-table">'
    wpage += f'<h1>{clean_title(seo_filter_text_custom(res.get("restitle", "")))}</h1>'
    
    if res.get('resfulltext'):
        wpage += f'<div class="seo-content">{seo_filter_text_custom(res["resfulltext"])}</div>'
    elif res.get('resshorttext'):
        wpage += f'<div class="seo-content">{seo_filter_text_custom(res["resshorttext"])}</div>'
    
    wpage += '</div>'
    
    return wpage


def build_bcpage_wp(
    bubbleid: int,
    domainid: int,
    debug: bool,
    agent: str,
    domain_data: Dict[str, Any],
    domain_settings: Dict[str, Any],
    artpageid: int = 0,
    artdomainid: int = 0
) -> str:
    """
    Build Business Collective page HTML (Action=2).
    Replicates seo_automation_build_bcpage from businesscollective-wp.php
    
    TODO: Full implementation needed - this is a placeholder
    """
    if not bubbleid or not domainid:
        return ""
    
    # Get bubblefeed data
    sql = """
        SELECT b.id, b.restitle, b.resfulltext, b.resshorttext, b.resfeedtext, b.linkouturl,
               IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category
        FROM bwp_bubblefeed b
        LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
        WHERE b.domainid = %s AND b.deleted != 1 AND b.id = %s
    """
    res = db.fetch_row(sql, (domainid, bubbleid))
    
    if not res:
        return ""
    
    # Build basic page HTML (placeholder - needs full implementation)
    bcpage = '<div class="seo-automation-main-table">'
    bcpage += f'<h1>{clean_title(seo_filter_text_custom(res.get("restitle", "")))} - Resources</h1>'
    
    if res.get('resfeedtext'):
        shorttext = res['resfeedtext']
        shorttext = shorttext.replace('Table of Contents', '').strip()
    elif res.get('resshorttext'):
        shorttext = res['resshorttext']
        shorttext = shorttext.replace('Table of Contents', '').strip()
    else:
        shorttext = ''
    
    if shorttext:
        bcpage += f'<div class="seo-content">{seo_filter_text_custom(shorttext)}</div>'
    
    bcpage += '</div>'
    
    return bcpage


def build_bubba_page_wp(
    bubbleid: int,
    domainid: int,
    debug: bool,
    agent: str,
    keyword: str,
    domain_data: Dict[str, Any],
    domain_settings: Dict[str, Any]
) -> str:
    """
    Build Bubba page HTML (Action=3).
    Replicates seo_automation_build_bubba_page from websitereferencebubba-wp.php
    
    TODO: Full implementation needed - this is a placeholder
    """
    if not bubbleid or not domainid:
        return ""
    
    # Get bubbafeed data
    sql = """
        SELECT ba.*, c.category, c.bubblefeedid AS catbubbleid, bb.categoryid
        FROM bwp_bubbafeed ba
        LEFT JOIN bwp_bubblefeed bb ON bb.id = ba.bubblefeedid
        LEFT JOIN bwp_bubblefeedcategory c ON c.id = bb.categoryid AND c.deleted != 1
        WHERE ba.id = %s AND ba.domainid = %s AND bb.deleted != 1 AND ba.deleted != 1
    """
    res = db.fetch_row(sql, (bubbleid, domainid))
    
    if not res:
        # Try by keyword
        sql = """
            SELECT ba.*, c.category, c.bubblefeedid AS catbubbleid, bb.categoryid
            FROM bwp_bubbafeed ba
            LEFT JOIN bwp_bubblefeed bb ON bb.id = ba.bubblefeedid
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = bb.categoryid AND c.deleted != 1
            WHERE ba.bubbatitle = %s AND ba.domainid = %s AND bb.deleted != 1 AND ba.deleted != 1
        """
        res = db.fetch_row(sql, (keyword, domainid))
    
    if not res:
        return ""
    
    # Build basic page HTML (placeholder - needs full implementation)
    wpage = '<div class="seo-automation-main-table">'
    wpage += f'<h1>{clean_title(seo_filter_text_custom(res.get("bubbatitle", "")))}</h1>'
    
    if res.get('resfulltext'):
        wpage += f'<div class="seo-content">{seo_filter_text_custom(res["resfulltext"])}</div>'
    
    wpage += '</div>'
    
    return wpage