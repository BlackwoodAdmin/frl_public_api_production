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
            import html
            is_bron_val = is_bron(domain_data.get('servicetype'))
            
            # Match PHP logic: elseif($silo[$i]['id'])
            if item.get('id'):
                # Build Resources link (Business Collective page - resfeedtext)
                # PHP condition: links_per_page >=1 || 1==1 (always true)
                if item.get('links_per_page', 0) >= 1 or True:  # Always true like PHP
                    if is_bron_val:
                        bclink = linkdomain + '/' + str(item['id']) + 'bc/'
                    else:
                        # Use toAscii(html_entity_decode(seo_text_custom(...))) for slug
                        slug_text = seo_text_custom(item['restitle'])  # seo_text_custom
                        slug_text = html.unescape(slug_text)  # html_entity_decode
                        slug_text = to_ascii(slug_text)  # toAscii
                        slug_text = slug_text.lower()  # strtolower
                        slug_text = slug_text.replace(' ', '-')  # str_replace(' ', '-', ...)
                        bclink = linkdomain + '/' + slug_text + '-' + str(item['id']) + 'bc/'
                    newsf = ' <a style="padding-left: 0px !important;" href="' + bclink + '">Resources</a>'
                else:
                    newsf = ''
                    bclink = ''
                
                # Main link logic (for resfulltext pages)
                # Check resourcesactive as string '1' or integer 1
                resourcesactive = str(domain_data.get('resourcesactive', ''))
                if resourcesactive == '1' or resourcesactive == 1:
                    # Resources active - show main article link (resfulltext) + Resources link (resfeedtext)
                    if (item.get('NoContent') == 0 or is_bron_val) and len(item.get('linkouturl', '').strip()) > 5:
                        # External link
                        foot += '<li><a style="padding-right: 0px !important;" href="' + item['linkouturl'] + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a>' + newsf + '</li>\n'
                    else:
                        # Internal link to main content page (resfulltext) - use toAscii(html_entity_decode(seo_text_custom(...))) for slug
                        slug_text = seo_text_custom(item['restitle'])  # seo_text_custom
                        slug_text = html.unescape(slug_text)  # html_entity_decode
                        slug_text = to_ascii(slug_text)  # toAscii
                        slug_text = slug_text.lower()  # strtolower
                        slug_text = slug_text.replace(' ', '-')  # str_replace(' ', '-', ...)
                        main_link = linkdomain + '/' + slug_text + '-' + str(item['id']) + '/'
                        foot += '<li><a style="padding-right: 0px !important;" href="' + main_link + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a>' + newsf + '</li>\n'
                else:
                    # Resources not active - show only Business Collective link (resfeedtext)
                    if not bclink:
                        # Build bclink if not already built
                        if is_bron_val:
                            bclink = linkdomain + '/' + str(item['id']) + 'bc/'
                        else:
                            slug_text = seo_text_custom(item['restitle'])
                            slug_text = html.unescape(slug_text)
                            slug_text = to_ascii(slug_text)
                            slug_text = slug_text.lower()
                            slug_text = slug_text.replace(' ', '-')
                            bclink = linkdomain + '/' + slug_text + '-' + str(item['id']) + 'bc/'
                    foot += '<li><a style="padding-right: 0px !important;" href="' + bclink + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a></li>\n'
                
                num_lnks += 1
            # Match PHP logic: elseif(strlen(trim($silo[$i]['linkouturl'])) > 5)
            elif len(item.get('linkouturl', '').strip()) > 5:
                # External link case - build Resources link if links_per_page >= 1
                if item.get('links_per_page', 0) >= 1:
                    # Use seo_filter_text_custom for this case (line 235 in PHP)
                    slug_text = seo_filter_text_custom(item['restitle'])
                    slug_text = html.unescape(slug_text)
                    slug_text = to_ascii(slug_text)
                    slug_text = slug_text.lower()
                    slug_text = slug_text.replace(' ', '-')
                    bclink = linkdomain + '/' + slug_text + '-' + str(item.get('id', '')) + 'bc/'
                    newsf = ' <a style="padding-left: 0px !important;" href="' + bclink + '">Resources</a>'
                else:
                    newsf = ''
                foot += '<li><a style="padding-right: 0px !important;" href="' + item['linkouturl'] + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a>' + newsf + '</li>\n'
                num_lnks += 1
        
        foot += '</ul>\n'
        foot += 'Articles</li>\n'
    
    # Add Blog and FAQ links if configured
    if domain_settings.get('blogUrl') and len(domain_settings['blogUrl']) > 10:
        foot += '<li><a class="url" style="width: 100%;font-size:12px;line-height:13px;" target="_blank" href="' + domain_settings['blogUrl'] + '">Blog</a></li>\n'
    
    if domain_settings.get('faqUrl') and len(domain_settings['faqUrl']) > 10:
        foot += '<li><a class="url" style="width: 100%;font-size:12px;line-height:13px;" target="_blank" href="' + domain_settings['faqUrl'] + '">FAQ</a></li>\n'
    
    # Add "Recent Post" section (drip content links) if conditions are met
    servicetype = domain_data.get('servicetype')
    dripcontent = domain_data.get('dripcontent', 0)
    if servicetype not in [10, 356] and dripcontent > 3:
        bubba_sql = """
            SELECT ba.* 
            FROM bwp_bubbafeed ba
            LEFT JOIN bwp_bubblefeed bb ON bb.id = ba.bubblefeedid
            WHERE ba.domainid = %s
            AND ba.deleted != 1
            AND bb.deleted != 1
            AND LENGTH(ba.resfulltext) > 300
            ORDER BY ba.id DESC
            LIMIT 20
        """
        allbubba = db.fetch_all(bubba_sql, (domainid,))
        
        if allbubba:
            foot += '<li>'
            foot += '<ul class="seo-sub-nav">\n'
            import html
            for bubba in allbubba:
                # Use toAscii(html_entity_decode(seo_text_custom(...))) for slug
                slug_text = seo_text_custom(bubba.get('bubbatitle', ''))  # seo_text_custom
                slug_text = html.unescape(slug_text)  # html_entity_decode
                slug_text = to_ascii(slug_text)  # toAscii
                slug_text = slug_text.lower()  # strtolower
                slug_text = slug_text.replace(' ', '-')  # str_replace(' ', '-', ...)
                slug = slug_text + '-' + str(bubba['id']) + 'dc'
                bubba_title = clean_title(html.unescape(seo_filter_text_custom(bubba.get('bubbatitle', ''))))
                foot += '<li><a style="padding-right: 0px !important;" href="' + linkdomain + '/' + slug + '">' + bubba_title + '</a></li>\n'
            foot += '</ul>\n'
            foot += 'Recent Post</li>\n'
    
    # Build final footer HTML
    if domain_data.get('wr_name'):
        ltest = domain_data['wr_name']
    else:
        ltest = domain_data['domain_name']
    
    foot += '</ul><a href="' + linkdomain + '/"><div class="seo-button-paid">&copy; ' + str(datetime.now().year) + ' ' + ltest + '</div></a></li></ul>\n'
    
    # Prepend wrapper divs (matching PHP structure)
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


def seo_filter_text_customapi(text: str) -> str:
    """Clean text similar to PHP seo_filter_text_customapi (for API output)."""
    import re
    text = text.strip()
    text = re.sub(r'&(amp;)+', '&', text)
    text = text.replace('&amp;amp;', '&amp;')
    text = text.replace('&amp;mdash;', '&mdash;')
    text = text.replace('&amp;nbsp;', '&nbsp;')
    text = text.replace('&amp;#', '&#')
    # Note: Does NOT decode &#39; and &#124; (commented out in PHP)
    return text


def trim_to_first_n_words(text: str, n: int) -> str:
    """Trim text to first N words (PHP bwp_shorten_string)."""
    words = text.split()
    if len(words) <= n:
        return text
    return ' '.join(words[:n]) + ' ...'


def to_ascii(text: str) -> str:
    """Convert text to ASCII (simplified version of PHP toAscii).
    Note: PHP toAscii expects text to already be processed by seo_text_custom and html_entity_decode.
    """
    import re
    # Text should already be processed by seo_text_custom and html_entity_decode before calling this
    text = text.replace(' &#x26;', '')
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


def custom_ucfirst_words(text: str) -> str:
    """Capitalize first letter of each word (PHP customUcfirstWords)."""
    if not text:
        return ''
    words = text.split()
    return ' '.join(word.capitalize() for word in words)


def seo_text_customamp(text: str) -> str:
    """Clean text similar to PHP seo_text_customamp."""
    text = text.replace("&amp;amp;", "&amp;")
    text = text.replace("&amp;amp;", "&amp;")
    return text


def seo_automation_add_text_link_new(text: str = '', kword: str = '', iurl: str = '', follow: str = '', title: str = '') -> str:
    """
    Add text link to content (PHP seo_automation_add_text_link_new).
    Replicates PHP function from functions.inc.php line 2273-2307.
    Skips first 4000 characters before searching for keyword.
    """
    import re
    import html
    
    if text and kword and iurl:
        # Clean keyword and text
        kword_clean = clean_title(kword)
        text = seo_text_customamp(text)
        
        # Skip the first 4000 characters (PHP line 2278-2280)
        initial_text = text[:4000]
        remaining_text = text[4000:]
        
        # Pattern to skip existing <a> tags and HTML tags, match keyword
        # PHP: /<a\b[^>]*>.*?<\/a>(*SKIP)(*FAIL)|<[^>]+>(*SKIP)(*FAIL)|\b{keyword}\b/i
        escaped_kword = re.escape(kword_clean)
        pattern = rf'(?:<a\b[^>]*>.*?</a>|<[^>]+>|\b{escaped_kword}\b)'
        
        replaced = False
        
        def replace_callback(match):
            nonlocal replaced
            match_str = match.group(0)
            # Check if this is the keyword (not an HTML tag)
            if not match_str.startswith('<') and match_str.lower() == kword_clean.lower():
                if not replaced:
                    replaced = True
                    title_attr = html.escape(title) if title else html.escape(kword_clean)
                    return f' <a title="{title_attr}" {follow} href="{iurl}">{match_str}</a>'
            return match_str
        
        remaining_text = re.sub(pattern, replace_callback, remaining_text, flags=re.IGNORECASE)
        
        # If no replacement was made, append link at end (PHP line 2297-2298)
        if not replaced:
            title_attr = html.escape(title) if title else html.escape(kword_clean)
            remaining_text = remaining_text + f' <a title="{title_attr}" {follow} href="{iurl}">{kword_clean}</a>'
        
        return initial_text + remaining_text
    else:
        return text


def seo_automation_add_text_link_newbc(text: str = '', kword: str = '', iurl: str = '', follow: str = '', title: str = '') -> str:
    """
    Add text link to content (PHP seo_automation_add_text_link_newbc).
    Replicates PHP function from functions.inc.php line 2309-2340.
    """
    import re
    import html
    
    if text and kword and iurl:
        # Clean keyword and text
        kword_clean = clean_title(kword)
        text = seo_text_customamp(text)
        
        # Pattern to skip existing <a> tags and HTML tags, match keyword
        # PHP: /<a\b[^>]*>.*?<\/a>(*SKIP)(*FAIL)|<[^>]+>(*SKIP)(*FAIL)|\b{keyword}\b/i
        escaped_kword = re.escape(kword_clean)
        pattern = rf'(?:<a\b[^>]*>.*?</a>|<[^>]+>|\b{escaped_kword}\b)'
        
        replaced = False
        
        def replace_callback(match):
            nonlocal replaced
            match_str = match.group(0)
            # Check if this is the keyword (not an HTML tag)
            if not match_str.startswith('<') and match_str.lower() == kword_clean.lower():
                if not replaced:
                    replaced = True
                    title_attr = html.escape(title) if title else html.escape(kword_clean)
                    return f' <a title="{title_attr}" {follow} target="_blank" href="{iurl}">{match_str}</a>'
            return match_str
        
        text = re.sub(pattern, replace_callback, text, flags=re.IGNORECASE)
        
        # If no replacement was made, append link at end
        if not replaced:
            title_attr = html.escape(title) if title else html.escape(kword_clean)
            text = text + f' <a title="{title_attr}" {follow} target="_blank" href="{iurl}">{kword_clean}</a>'
        
        return text
    else:
        return text


def insert_after_first_heading(html_string: str, string_to_insert: str) -> str:
    """
    Insert string after the second heading tag (PHP insertAfterFirstHeading).
    Replicates PHP function from functions.inc.php line 151-178.
    """
    import re
    
    heading_count = 0
    replace_count = 0
    
    def replace_callback(match):
        nonlocal heading_count, replace_count
        heading_count += 1
        
        # If this is the second heading tag, append the string to insert
        if heading_count == 2:
            replace_count = 1
            return string_to_insert + match.group(0)
        
        # Return the original heading tag for all other cases
        return match.group(0)
    
    # Pattern to match heading tags: <h1> through <h6>
    pattern = r'<h[1-6][^>]*>.*?</h[1-6]>'
    result = re.sub(pattern, replace_callback, html_string, flags=re.IGNORECASE | re.DOTALL)
    
    # If no replacement was made, prepend the string (PHP line 176)
    if replace_count == 0:
        result = string_to_insert + result
    
    return result


def check_image_src_gpt(string: str) -> int:
    """
    Check if string contains specific image src pattern (PHP checkImageSrcGPT).
    Replicates PHP function from functions.inc.php line 180-192.
    Returns 1 if pattern NOT found, 0 if found.
    """
    import re
    
    # Regular expression to find <img> tags with a specific src
    pattern = r'<img[^>]+src\s*=\s*["\']https://services6\.imagehosting\.space/images/[^"\']+["\'][^>]*>'
    
    # Check if the pattern is found in the string
    if re.search(pattern, string, re.IGNORECASE):
        # If found, return 0
        return 0
    
    # If not found, return 1
    return 1


def is_bron(servicetype: Optional[int]) -> bool:
    """Check if service type is BRON, matching PHP isBRON function."""
    if not servicetype:
        return False
    # Use %% to escape % for PyMySQL (which uses Python % formatting)
    sql = "SELECT * FROM bwp_services WHERE servicetype LIKE 'BRON %%' AND servicetype != 'SEOM 5' AND id = %s ORDER BY keywords"
    result = db.fetch_all(sql, (servicetype,))
    return bool(result)


def is_seom(servicetype: Optional[int]) -> bool:
    """Check if service type is SEOM, matching PHP isSEOM function."""
    if not servicetype:
        return False
    # Use %% to escape % for PyMySQL (which uses Python % formatting)
    sql = "SELECT * FROM bwp_services WHERE servicetype LIKE 'SEOM %%' AND servicetype != 'SEOM 5' AND id = %s ORDER BY keywords"
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
                    'post_content': '',
                    'comment_status': 'closed',
                    'ping_status': 'closed',
                    'post_date': str(post_date),
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
            
            # Convert datetime to string if needed
            post_date = page.get('createdDate', '')
            if post_date and hasattr(post_date, 'strftime'):
                post_date = post_date.strftime('%Y-%m-%d %H:%M:%S')
            elif post_date is None:
                post_date = ''
            
            pagearray = {
                'pageid': str(pageid),
                'canonical': '',
                'post_title': keyword,
                'post_type': 'page',
                'post_content': '',
                'comment_status': 'closed',
                'ping_status': 'closed',
                'post_date': str(post_date),
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
        
        # Convert datetime to string if needed
        post_date = bcpage.get('createdDate', '')
        if post_date and hasattr(post_date, 'strftime'):
            post_date = post_date.strftime('%Y-%m-%d %H:%M:%S')
        elif post_date is None:
            post_date = ''
        
        bcpagearray = {
            'pageid': str(pageid) + 'bc',
            'post_title': keyword.lower() + ' - Resources',
            'post_type': 'page',
            'post_content': '',
            'comment_status': 'closed',
            'ping_status': 'closed',
            'post_date': str(post_date),
            'post_excerpt': sorttext,
            'post_name': slug,
            'post_status': 'publish',
            'post_metatitle': metaTitle,
            'post_metakeywords': keyword.lower() + ' Resources',
            'template_file': template_file or ''
        }
        pagesarray.append(bcpagearray)
    
    return pagesarray


def extract_youtube_video_id(video_url: str) -> str:
    """
    Extract YouTube video ID from various URL formats.
    Replicates the PHP video URL cleaning logic from websitereference-wp.php lines 366-383
    """
    import re
    if not video_url or not video_url.strip():
        return ""
    
    # Clean the video URL
    vid = str(video_url).strip()
    vid = vid.replace('https://www.', '')
    vid = vid.replace('http://www.', '')
    vid = vid.replace('http://', '')
    vid = vid.replace('//', '')
    vid = vid.replace('youtu.be/', '')
    vid = vid.replace('youtube.com/embed/', '')
    vid = vid.replace('youtube.com/watch?v=', '')
    vid = vid.replace('www.', '')
    
    # Remove &feature=... and similar parameters
    vid = re.sub(r'&.*feature.*', '', vid)
    vid = vid.strip()
    
    return vid


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
    """
    import html
    import re
    from urllib.parse import quote
    from datetime import datetime, timedelta
    import random
    
    if not bubbleid or not domainid:
        return ""
    
    # Get bubblefeed data - handle multiple scenarios (PHP lines 52-108)
    res = None
    if offpageid != 0 and support != 1:
        sql = """
            SELECT bo.id, bo.bubblefeedid, b.restitle, bo.title, bo.resfulltext, b.resshorttext, 
                   b.linkouturl, b.resaddress, b.resgooglemaps, b.resphone, bo.resvideo, 
                   b.resvideo AS resvideobubble, b.resname,
                   IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category
            FROM bwp_bubblefeedoffsite bo
            LEFT JOIN bwp_bubblefeed b ON b.id = bo.bubblefeedid
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
            WHERE bo.id = %s AND bo.domainid = %s
        """
        res = db.fetch_row(sql, (offpageid, offdomainid))
    elif support == 1 and (is_seom(domain_data.get('servicetype')) or is_bron(domain_data.get('servicetype'))):
        sql = """
            SELECT b.restitle, b.title, b.resfulltext, b.resshorttext, b.linkouturl, b.resaddress, 
                   b.resgooglemaps, b.resphone, b.resvideo, b.resname, b.bubblefeedid,
                   b.resgoogle, b.resfb, b.resx, b.reslinkedin, b.resinstagram, b.restiktok, b.respinterest,
                   IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category
            FROM bwp_bubblefeedsupport b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
            WHERE b.id = %s AND b.domainid = %s
        """
        res = db.fetch_row(sql, (bubbleid, domainid))
    elif artpageid != 0:
        sql = """
            SELECT b.id, b.restitle, b.title, b.resfulltext, b.resshorttext, b.linkouturl, 
                   b.resaddress, b.resgooglemaps, b.resphone, b.resvideo, b.resname,
                   IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category
            FROM bwp_bubblefeed b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
            WHERE b.id = %s AND b.domainid = %s AND b.deleted != 1
        """
        res = db.fetch_row(sql, (artpageid, artdomainid))
    else:
        sql = """
            SELECT b.id, b.restitle, b.title, b.resfulltext, b.resshorttext, b.linkouturl, 
                   b.categoryid AS bubblecategoryid, b.resphone, b.resvideo, b.resaddress, 
                   b.resgooglemaps, b.resname, b.resgoogle, b.resfb, b.resx, b.reslinkedin, 
                   b.resinstagram, b.restiktok, b.respinterest,
                   IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category, c.bubblefeedid
            FROM bwp_bubblefeed b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
            WHERE b.id = %s AND b.domainid = %s AND b.deleted != 1
        """
        res = db.fetch_row(sql, (bubbleid, domainid))
    
    # Fallback: try to find by keyword (PHP lines 97-108)
    if not res and keyword:
        sql = """
            SELECT b.id, b.restitle, b.title, b.resfulltext, b.resshorttext, b.linkouturl, 
                   b.resphone, b.resvideo, b.resaddress, b.resgooglemaps, b.resname, b.NoContent,
                   b.resgoogle, b.resfb, b.resx, b.reslinkedin, b.resinstagram, b.restiktok, b.respinterest,
                   IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category, c.bubblefeedid
            FROM bwp_bubblefeed b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
            WHERE b.restitle = %s AND b.domainid = %s AND b.deleted != 1
        """
        res = db.fetch_row(sql, (keyword, domainid))
    
    if not res:
        return ""
    
    # Build link domain (PHP lines 208-232)
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
    
    # Build resurl (PHP lines 243-264)
    if artpageid != 0 or offpageid != 0:
        resurl = linkdomain
    else:
        if res.get('categoryid'):
            if res.get('bubblefeedid') == res.get('id'):
                resurl = '/'
            else:
                urltitle = seo_filter_text_custom(res.get('category', ''))
                slug_text = seo_text_custom(urltitle)
                slug_text = html.unescape(slug_text)
                slug_text = to_ascii(slug_text)
                slug_text = slug_text.lower()
                slug_text = slug_text.replace(' ', '-')
                resurl = linkdomain + '/' + slug_text + '-' + str(res.get('bubblefeedid', res.get('id', '')))
        elif is_seom(domain_data.get('servicetype')) and res.get('linkouturl'):
            resurl = res['linkouturl']
        else:
            resurl = '/'
    
    # Start building page (PHP line 136)
    if domain_data.get('resourcesactive') != 1:
        return '<p>This feature is not available for your current package. Please upgrade your package. [ID-01]</p>'
    
    wpage = '<div class="seo-automation-main-table" style="margin-left:auto;margin-right:auto;display:block;">\n'
    wpage += '<div class="seo-automation-spacer"></div>\n'
    
    # Check if resfulltext contains Bootstrap container classes and add Bootstrap CSS/JS if needed (PHP lines 266-275)
    resfulltext = res.get('resfulltext', '')
    if resfulltext and 'container justify-content-center' in resfulltext.lower():
        wpage += '''
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@3.3.7/dist/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">

<script src="https://cdn.jsdelivr.net/npm/bootstrap@3.3.7/dist/js/bootstrap.min.js" integrity="sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa" crossorigin="anonymous"></script>

<style>.wr-fulltext img {height: auto !important;min-width:100%;}@media (min-width: 992px){.wr-fulltext img {min-width:0;}}.container.justify-content-center {max-width:100%;margin-bottom:15px;}.ngodkrbsitr-spacer{clear:both;}.seo-automation-main-table h1:after, .seo-automation-main-table h2:after, .seo-automation-main-table h3:after, .seo-automation-main-table h4:after, .seo-automation-main-table h5:after, .seo-automation-main-table h6:after {display: none !important;clear: none !important;} .seo-automation-main-table h1, .seo-automation-main-table h2, .seo-automation-main-table h3, .seo-automation-main-table h4, .seo-automation-main-table h5, .seo-automation-main-table h6 {clear: none !important;}.seo-automation-main-table .row .col-md-6 {	/* display:list-item; */ } </style>
'''
    
    # Handle YouTube video embedding (PHP lines 282-465)
    # Priority: resvideo -> resvideobubble -> domain_data['wr_video']
    video_id = ""
    if res.get('resvideo') and res.get('resvideo').strip():
        video_id = extract_youtube_video_id(res['resvideo'])
    elif res.get('resvideobubble') and res.get('resvideobubble').strip():
        video_id = extract_youtube_video_id(res['resvideobubble'])
    elif domain_data.get('wr_video') and str(domain_data.get('wr_video', '')).strip():
        video_id = extract_youtube_video_id(domain_data['wr_video'])
    
    if video_id:
        title_attr = clean_title(seo_filter_text_custom(res.get("restitle", "")))
        wpage += f'<div class="vid-container dddd"><iframe title="{title_attr}" style="max-width:100%;margin-bottom:20px;" src="//www.youtube.com/embed/{video_id}" width="900" height="480"></iframe></div>'
        wpage += '<div class="seo-automation-spacer"></div>\n'
    
    # Handle snapshot/image insertion (PHP lines 327-463)
    if domain_data.get('showsnapshot') == 1 and check_image_src_gpt(html.unescape(seo_filter_text_custom(res.get('resfulltext', '')))) == 1:
        moneynofollow = ''
        if artpageid != 0 and (artdomainid == 87252 or True):
            moneynofollow = ''
        
        if not res.get('linkouturl'):
            im = f'<a{moneynofollow} style="display: inline;" href="{resurl}">'
        else:
            im = f'<a{moneynofollow} href="{res["linkouturl"].replace("&amp;", "&")}">'
        
        im += f'<img src="//imagehosting.space/feed/pageimage.php?domain={domain_data["domain_name"]}" class="align-left" style="width:320px !important;height:260px;" alt="{clean_title(seo_filter_text_custom(res.get("restitle", "")))}">'
        im += '</a>'
        
        # Insert image after first heading (PHP line 337)
        resfulltext = html.unescape(seo_filter_text_custom(res.get('resfulltext', '')))
        resfulltext = insert_after_first_heading(resfulltext, im)
        res['resfulltext'] = html.escape(resfulltext)
    
    # Build text content with keyword linking (PHP lines 466-557)
    textkeywd = clean_title(seo_filter_text_custom(res.get('restitle', '')))
    
    if len(res.get('resfulltext', '').strip()) > 50 and domain_data.get('writerlock') != 1:
        linkedtexted = html.unescape(seo_filter_text_custom(res.get('resfulltext', '')))
        
        # Determine URL for linking (PHP lines 472-485)
        if offpageid != 0:
            # Build offselfurl (simplified - would need full off_category logic)
            theurl = linkdomain
        elif artpageid != 0:
            # Build artselfurl (simplified - would need full art_category logic)
            theurl = linkdomain
        elif len(res.get('linkouturl', '').strip()) <= 0:
            theurl = resurl
        else:
            theurl = res.get('linkouturl', '').replace('&amp;', '&')
        
        # Add main keyword link (PHP line 487)
        moneynofollow = ''
        linkedtexted = seo_automation_add_text_link_new(linkedtexted, res.get('restitle', ''), theurl, moneynofollow)
        
        # Add support keyword links for SEOM/BRON (PHP lines 488-532)
        if offdomainid != 0:
            # Support keywords for offsite (PHP lines 488-504)
            support_sql = """
                SELECT id, restitle FROM bwp_bubblefeedsupport 
                WHERE bubblefeedid = %s AND domainid = %s AND deleted != 1 AND LENGTH(resfulltext) > 300
            """
            thesupports = db.fetch_all(support_sql, (res.get('bubblefeedid', res.get('id', '')), offdomainid))
            for thesupport in thesupports:
                # Build offsupportselfurl (simplified)
                offsupportselfurl = linkdomain + '/' + seo_slug(seo_filter_text_custom(thesupport['restitle'])) + '-' + str(thesupport['id']) + '/'
                linkedtexted = seo_automation_add_text_link_new(linkedtexted, thesupport['restitle'], offsupportselfurl, moneynofollow)
        elif support == 0 and is_seom(domain_data.get('servicetype')):
            # Support keywords for SEOM (PHP lines 505-512)
            support_sql = """
                SELECT id, restitle FROM bwp_bubblefeedsupport 
                WHERE bubblefeedid = %s AND domainid = %s AND deleted != 1 AND LENGTH(resfulltext) > 300
            """
            thesupports = db.fetch_all(support_sql, (bubbleid, domainid))
            for thesupport in thesupports:
                thesupporturl = linkdomain + '/' + seo_slug(seo_filter_text_custom(thesupport['restitle'])) + '-' + str(thesupport['id']) + '/'
                linkedtexted = seo_automation_add_text_link_new(linkedtexted, thesupport['restitle'], thesupporturl, moneynofollow)
        elif support != 0 and (is_seom(domain_data.get('servicetype')) or is_bron(domain_data.get('servicetype'))):
            # Support keywords for support page (PHP lines 515-532)
            mainkw_sql = "SELECT restitle, linkouturl, id FROM bwp_bubblefeed WHERE id = %s"
            mainkw = db.fetch_row(mainkw_sql, (res.get('bubblefeedid', res.get('id', '')),))
            if mainkw:
                if len(mainkw.get('linkouturl', '')) > 5:
                    mainkwurl = mainkw['linkouturl']
                else:
                    mainkwurl = linkdomain + '/' + seo_slug(seo_filter_text_custom(mainkw['restitle'])) + '-' + str(mainkw['id']) + '/'
                linkedtexted = seo_automation_add_text_link_new(linkedtexted, mainkw['restitle'], mainkwurl.replace('&amp;', '&'), moneynofollow)
                
                # Get other support keyword
                osupkw_sql = """
                    SELECT restitle, id FROM bwp_bubblefeedsupport 
                    WHERE bubblefeedid = %s AND restitle != %s
                """
                osupkw = db.fetch_row(osupkw_sql, (res.get('bubblefeedid', res.get('id', '')), res.get('restitle', '')))
                if osupkw:
                    osupkwurl = linkdomain + '/' + seo_slug(seo_filter_text_custom(osupkw['restitle'])) + '-' + str(osupkw['id']) + '/'
                    linkedtexted = seo_automation_add_text_link_new(linkedtexted, osupkw['restitle'], osupkwurl.replace('&amp;', '&'), moneynofollow)
        
        wpage += linkedtexted
    elif len(res.get('resshorttext', '').strip()) > 50:
        # Use shorttext if fulltext not available (PHP lines 535-557)
        linkedtexted = html.unescape(res.get('resshorttext', ''))
        
        # Determine URL for linking
        if offpageid != 0:
            theurl = linkdomain
        elif artpageid != 0:
            if domain_data.get('writerlock') == 1:
                linkedtexted = ''
            theurl = linkdomain
        elif len(res.get('linkouturl', '').strip()) < 5:
            theurl = resurl
        else:
            theurl = res.get('linkouturl', '').replace('&amp;', '&')
        
        linkedtexted = seo_automation_add_text_link_new(linkedtexted, res.get('restitle', ''), theurl, moneynofollow)
        wpage += linkedtexted
    
    wpage += '</div>\n'
    
    # Related posts - drip content (bubbafeed) (PHP lines 879-917)
    if res.get('id'):
        bubba_sql = """
            SELECT * FROM bwp_bubbafeed
            WHERE bubblefeedid = %s AND active = '1' 
            AND char_length(resfulltext) > 300 AND deleted != '1'
            ORDER BY createdDate DESC
        """
        resbubba = db.fetch_all(bubba_sql, (res['id'],))
        
        if resbubba:
            wpage += '<div class="seo-automation-spacer"></div>\n'
            wpage += '<div class="seo-automation-container-wr-full">\n'
            
            for bubba in resbubba:
                title = clean_title(seo_filter_text_custom(bubba.get('bubbatitle', '')))
                titlelink = title.lower().replace(' ', '-')
                titlelink = to_ascii(html.unescape(titlelink))
                resurl_bubba = linkdomain + '/' + seo_text_custom(titlelink) + '-' + str(bubba['id']) + 'dc'
                
                wpage += '<div class="seo-automation-containerwr moinfomation">\n'
                wpage += f'<h2 class="h2"><a target="_top" title="{title}" href="{resurl_bubba}">{title}</a></h2>\n'
                
                bubbatext = strip_html(html.unescape(seo_filter_text_custom(bubba.get('resfulltext', ''))))
                bubbatext = trim_to_first_n_words(bubbatext, 75)
                bubbatext = bubbatext.replace('//gallery.imagehosting.space/gallery/', '//gallery.imagehosting.space/thumbs/')
                wpage += bubbatext
                wpage += '</div>\n'
                wpage += '<div class="seo-automation-spacer"></div>\n'
            
            wpage += '</div>\n'
    
    # Related posts - related articles (PHP lines 918-1020)
    if res.get('restitle') and res.get('restitle') == res.get('category'):
        # Get related articles from same category (PHP lines 918-929)
        related_sql = """
            SELECT b.*, c.category
            FROM bwp_bubblefeed b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid
            WHERE b.categoryid = %s AND b.restitle != %s
            AND b.active = '1' AND b.deleted != '1' AND c.deleted != 1
            ORDER BY createdDate DESC
        """
        resrelated = db.fetch_all(related_sql, (res.get('categoryid', ''), res.get('restitle', '')))
        
        if resrelated:
            wpage += '<h2 class="h1">Related Posts</h2>\n'
            wpage += '<div class="seo-automation-spacer"></div>\n'
            wpage += '<div class="seo-automation-container-wr-full">\n'
            
            for rel in resrelated:
                resfulltext_rel = html.unescape(seo_filter_text_custom(rel.get('resfulltext', '')))
                if len(resfulltext_rel) > 50:
                    wpage += '<div class="seo-automation-containerwr">\n'
                    titledecoded = seo_filter_text_custom(rel.get('restitle', ''))
                    wpage += f'<h2 class="h2"><a target="_top" title="{titledecoded}" href="/">{titledecoded}</a></h2>\n'
                    wpage += resfulltext_rel
                    wpage += '<div class="seo-automation-spacer"></div>\n'
                    
                    # Get bubbafeed for related article (PHP lines 977-1016)
                    bubba_rel_sql = """
                        SELECT * FROM bwp_bubbafeed
                        WHERE bubblefeedid = %s AND active = '1' 
                        AND char_length(resfulltext) > 300 AND deleted != '1'
                        ORDER BY createdDate DESC
                    """
                    resbubba_rel = db.fetch_all(bubba_rel_sql, (rel['id'],))
                    
                    if resbubba_rel and domain_data.get('servicetype') != 10:
                        for bubba_rel in resbubba_rel:
                            title_rel = clean_title(seo_filter_text_custom(bubba_rel.get('bubbatitle', '')))
                            titlelink_rel = title_rel.lower().replace(' ', '-')
                            titlelink_rel = to_ascii(html.unescape(titlelink_rel))
                            resurl_bubba_rel = linkdomain + '/' + seo_text_custom(titlelink_rel) + '-' + str(bubba_rel['id']) + 'dc'
                            
                            wpage += '<div class="seo-automation-containerwr moinfomation">\n'
                            wpage += f'<h2 class="h2"><a target="_top" title="{title_rel}" href="{resurl_bubba_rel}">{title_rel}</a></h2>\n'
                            
                            bubbatext_rel = strip_html(html.unescape(seo_filter_text_custom(bubba_rel.get('resfulltext', ''))))
                            bubbatext_rel = trim_to_first_n_words(bubbatext_rel, 75)
                            bubbatext_rel = bubbatext_rel.replace('//gallery.imagehosting.space/gallery/', '//gallery.imagehosting.space/thumbs/')
                            wpage += bubbatext_rel
                            wpage += '</div>\n'
                            wpage += '<div class="seo-automation-spacer"></div>\n'
                    
                    wpage += '</div>\n'
            
            wpage += '</div>\n'
    
    # Google Maps section (PHP lines 1022-1487)
    ssmap = 0
    if domain_data.get('showmap'):
        if domain_data.get('wr_address') or res.get('resaddress'):
            map_val = 0
            addres = res.get('resaddress') or domain_data.get('wr_address', '')
            phon = res.get('resphone') or domain_data.get('wr_phone', '')
            
            stadd = ''
            cty = ''
            state = ''
            zip_code = ''
            mapurl = ''
            
            if addres:
                address = seo_filter_text_custom(addres)
                address = html.unescape(address)
                addressarray = address.split(',')
                if len(addressarray) == 3:
                    stzipstr = addressarray[2]
                    stziparray = stzipstr.strip().split(' ')
                    if len(stziparray) == 2:
                        stadd = addressarray[0].strip()
                        cty = addressarray[1].strip()
                        state = stziparray[0].strip()
                        zip_code = stziparray[1].strip()
                        map_val = 1
                    elif len(stziparray) == 3:
                        stadd = addressarray[0].strip()
                        cty = addressarray[1].strip()
                        state = stziparray[0].strip()
                        zip_code = stziparray[1].strip()
                        zip_code += ' ' + stziparray[2].strip()
                        map_val = 1
            
            if map_val == 1:
                wpage += '<div class="seo-automation-spacer"></div>\n'
                wpage += '<div class="google-map">\n'
                mpadd = ''
                
                if res.get('resname'):
                    wpage += '<div itemscope itemtype="http://schema.org/LocalBusiness">\n'
                    wpage += f'<span itemprop="name" style=""><strong>{seo_filter_text_customapi(res["resname"])}</strong></span> '
                    if res.get('resgooglemaps'):
                        wpage += f'<a href="{res["resgooglemaps"]}" title="Find us on Google" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="https://seopanel.imagehosting.space/images/maps15_bnuw3a_32dp.ico" border="0" width="16" alt="Best Seo Wordpress Plugin"></a>'
                    mpadd = res['resname']
                    ssmap = 1
                elif domain_data.get('wr_name'):
                    wpage += '<div itemscope itemtype="http://schema.org/LocalBusiness">\n'
                    wpage += f'<span itemprop="name" style=""><strong>{seo_filter_text_customapi(domain_data["wr_name"])}</strong></span> '
                    if res.get('resgooglemaps'):
                        wpage += f'<a href="{res["resgooglemaps"]}" title="Find us on Google" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="https://seopanel.imagehosting.space/images/maps15_bnuw3a_32dp.ico" border="0" width="16" alt="Best Seo Wordpress Plugin"></a>'
                    mpadd = domain_data['wr_name']
                    ssmap = 1
                
                if phon:
                    wpage += f'<div style="" itemprop="telephone">{phon}</div>\n'
                
                cntry = domain_data.get('domain_country', '')
                wpage += '<div itemprop="address" itemscope itemtype="http://schema.org/PostalAddress">\n'
                wpage += f'<div style="" itemprop="streetAddress">{stadd}</div>\n'
                wpage += f'<span style="" itemprop="addressLocality">{cty}</span>\n'
                wpage += f'<span style="" itemprop="addressRegion">{state}</span>\n'
                wpage += f'<span style="" itemprop="postalCode">{zip_code}</span>\n'
                wpage += f'<span style="display:none !important;" itemprop="addressCountry">{cntry}</span>\n'
                
                imagesrc = '//imagehosting.space/feed/pageimage.php?domain=' + domain_data['domain_name']
                wpage += f'<meta itemprop="image" content="{imagesrc}"></meta>\n'
                wpage += '</div>\n'
                
                # Build map URL
                if mpadd:
                    mapurl = f'https://www.google.com/maps/embed/v1/place?key=AIzaSyDET-f-9dCENEEt8nU2MLOXluoEtrq2k5o&q={quote(mpadd)}+{quote(addres.replace(",", ""))}'
                else:
                    mapurl = f'https://www.google.com/maps/embed/v1/place?key=AIzaSyDET-f-9dCENEEt8nU2MLOXluoEtrq2k5o&q={quote(addres.replace(",", ""))}'
                
                wpage += f'<iframe title="{mpadd}" width="280" height="160" style="border:0;overflow:hidden;" src="{mapurl}"></iframe>\n'
                
                if mpadd:
                    wpage += f'<br /><a href="https://maps.google.com/maps?q={quote(mpadd)}+{quote(addres.replace(",", ""))}" style="color:#0000FF;text-align:left">View Larger Map</a>\n'
                else:
                    wpage += f'<br /><a href="https://maps.google.com/maps?q={quote(addres.replace(",", ""))}" style="color:#0000FF;text-align:left">View Larger Map</a>\n'
                
                # Reviews schema (PHP lines 1137-1150)
                if domain_settings.get('reviewsch') == 1:
                    created_date = domain_data.get('createdDate', '')
                    if created_date:
                        if isinstance(created_date, str):
                            try:
                                past = datetime.strptime(created_date, '%Y-%m-%d %H:%M:%S')
                            except:
                                past = datetime.now() - timedelta(days=365)
                        else:
                            past = created_date
                    else:
                        past = datetime.now() - timedelta(days=365)
                    
                    now = datetime.now()
                    days_old = (now - past).days
                    rating = round(random.uniform(4.7, 4.9), 1)
                    
                    wpage += f'''
<div itemscope itemtype="https://schema.org/Product">
    <span class="product_name" itemprop="name">{mpadd}</span>&nbsp; &nbsp;<img src="/wp-content/themes/woodmart-child/4.9stars.png" style="max-width:100px"/>
    <div itemprop="aggregateRating" itemscope itemtype="https://schema.org/AggregateRating">
        Rated <span itemprop="ratingValue">{rating}</span>/5 based on <span itemprop="reviewCount">{days_old}</span> customer reviews
    </div>
</div>
'''
                
                wpage += '</div>\n'
    
    # Social media icons (PHP lines 1493-1508)
    if (len(res.get('resgoogle', '')) > 10 or len(res.get('resfb', '')) > 10 or 
        len(res.get('resx', '')) > 10 or len(res.get('reslinkedin', '')) > 10 or
        len(res.get('resinstagram', '')) > 10 or len(res.get('restiktok', '')) > 10 or
        len(res.get('respinterest', '')) > 10):
        if len(res.get('resgoogle', '')) > 10:
            wpage += f'<a href="{res["resgoogle"]}" title="{res.get("restitle", "")} - Find us on Google" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//seopanel.imagehosting.space/images/maps15_bnuw3a_32dp.ico" border="0" width="16" alt="{res.get("restitle", "")}"></a>'
        if len(res.get('resfb', '')) > 10:
            wpage += f'<a href="{res["resfb"]}" title="{res.get("restitle", "")} - Follow us on Facebook" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//imagehosting.space/images/fbfavicon.ico" width="16" alt="{res.get("restitle", "")}"></a>'
        if len(res.get('resx', '')) > 10:
            wpage += f'<a href="{res["resx"]}" title="{res.get("restitle", "")} - Follow us on X" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//www.x.com/favicon.ico" width="16" alt="{res.get("restitle", "")}"></a>'
        if len(res.get('reslinkedin', '')) > 10:
            wpage += f'<a href="{res["reslinkedin"]}" title="{res.get("restitle", "")} - Follow us on LinkedIn" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//imagehosting.space/images/linkfavicon.ico" border="0" width="16" alt="{res.get("restitle", "")}"></a>'
        if len(res.get('resinstagram', '')) > 10:
            wpage += f'<a href="{res["resinstagram"]}" title="{res.get("restitle", "")} - Follow us on Instagram" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//www.instagram.com/favicon.ico" border="0" width="16" alt="{res.get("restitle", "")}"></a>'
        if len(res.get('restiktok', '')) > 10:
            wpage += f'<a href="{res["restiktok"]}" title="{res.get("restitle", "")} - Follow us on TikTok" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//www.tiktok.com/favicon.ico" border="0" width="16" alt="{res.get("restitle", "")}"></a>'
        if len(res.get('respinterest', '')) > 10:
            wpage += f'<a href="{res["respinterest"]}" title="{res.get("restitle", "")} - Follow us on Penterest" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//www.pinterest.com/favicon.ico" border="0" width="16" alt="{res.get("restitle", "")}"></a>'
    
    wpage += '</div>\n'
    
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
    """
    if not bubbleid or not domainid:
        return ""
    
    import html
    import re
    from urllib.parse import quote
    
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
    
    # Build domain link
    if domain_settings.get('usedurl') == 1 and domain_data.get('domain_url'):
        dl = domain_data['domain_url'].rstrip('/')
    else:
        if domain_data.get('ishttps') == 1:
            dl = 'https://'
        else:
            dl = 'http://'
        if domain_data.get('usewww') == 1:
            dl += 'www.' + domain_data['domain_name']
        else:
            dl += domain_data['domain_name']
    
    # Build resurl
    if len(res.get('linkouturl', '')) > 5:
        resurl = res['linkouturl'].strip()
    else:
        resurl = dl + '/' + seo_slug(seo_filter_text_custom(res['restitle'])) + '-' + str(res['id']) + '/'
    
    # Start building page
    bcpage = '<div class="seo-automation-main-table" style="margin-left:auto;margin-right:auto;display:block;">\n'
    bcpage += '<div class="seo-automation-spacer"></div>\n'
    
    # Handle video or image
    servicetype = domain_data.get('servicetype')
    isSEOM_val = is_seom(servicetype)
    isBRON_val = is_bron(servicetype)
    
    if not domain_data.get('wr_video'):
        bcpage += f'<h2 style="text-align:center;margin:0 0 15px 0;"><a href="{resurl}" target="_blank">{clean_title(seo_filter_text_custom(res.get("restitle", "")))}</a></h2>\n'
        
        # Support links for SEOM/BRON
        if isSEOM_val or isBRON_val:
            support_sql = """
                SELECT restitle, id FROM bwp_bubblefeedsupport 
                WHERE domainid = %s AND bubblefeedid = %s AND deleted != 1 AND LENGTH(resfulltext) > 300
            """
            supportkwords = db.fetch_all(support_sql, (domainid, res['id']))
            if supportkwords:
                supportlks = ''
                for support in supportkwords:
                    # PHP line 144: Use toAscii(html_entity_decode(seo_text_custom(...))) for URL
                    import html
                    slug_text = seo_text_custom(support['restitle'])
                    slug_text = html.unescape(slug_text)
                    slug_text = to_ascii(slug_text)
                    slug_text = slug_text.lower()
                    slug_text = slug_text.replace(' ', '-')
                    resurl1 = dl + '/' + slug_text + '-' + str(support['id']) + '/'
                    supportlks += f' <strong><a href="{resurl1}" style="">{clean_title(seo_filter_text_custom(support["restitle"]))}</a></strong> -  '
                supportlks = supportlks.rstrip(' - ')
                bcpage += supportlks + '<br>\n'
        
        if domain_data.get('showsnapshot') == 1:
            bcpage += f'<a href="{resurl}" target="_blank"><img src="//imagehosting.space/feed/pageimage.php?domain={domain_data["domain_name"]}" alt="{clean_title(seo_filter_text_custom(res.get("restitle", "")))}" style="width:160px !important;height:130px;" class="align-left"></a>\n'
    else:
        # Video
        vid = extract_youtube_video_id(domain_data['wr_video'])
        if vid:
            bcpage += f'<div class="vid-container"><iframe style="max-width:100% !important;margin-bottom:20px;" src="//www.youtube.com/embed/{vid}" width="900" height="480"></iframe></div>\n'
            bcpage += '<div class="seo-automation-spacer"></div>\n'
        
        bcpage += f'<h2 style="text-align:center;margin:0 0 15px 0;"><a href="{resurl}" target="_blank">{clean_title(seo_filter_text_custom(res.get("restitle", "")))}</a></h2>\n'
        
        # Support links for SEOM/BRON
        if isSEOM_val or isBRON_val:
            support_sql = """
                SELECT restitle, id FROM bwp_bubblefeedsupport 
                WHERE domainid = %s AND bubblefeedid = %s AND deleted != 1 AND LENGTH(resfulltext) > 300
            """
            supportkwords = db.fetch_all(support_sql, (domainid, res['id']))
            if supportkwords:
                supportlks = ''
                for support in supportkwords:
                    # PHP line 186: Use toAscii(html_entity_decode(seo_text_custom(...))) for URL
                    import html
                    slug_text = seo_text_custom(support['restitle'])
                    slug_text = html.unescape(slug_text)
                    slug_text = to_ascii(slug_text)
                    slug_text = slug_text.lower()
                    slug_text = slug_text.replace(' ', '-')
                    resurl1 = dl + '/' + slug_text + '-' + str(support['id']) + '/'
                    supportlks += f' <strong><a href="{resurl1}" style="">{clean_title(seo_filter_text_custom(support["restitle"]))}</a></strong> -  '
                supportlks = supportlks.rstrip(' - ')
                bcpage += supportlks + '<br>\n'
    
    # Get resfeedtext or resshorttext
    if res.get('resfeedtext') and res['resfeedtext'].strip():
        shorttext = res['resfeedtext']
        shorttext = shorttext.replace('Table of Contents', '').strip()
    elif res.get('resshorttext') and res['resshorttext'].strip():
        shorttext = res['resshorttext']
        shorttext = shorttext.replace('Table of Contents', '').strip()
    else:
        shorttext = ''
    
    if shorttext:
        shorttext = html.unescape(str(shorttext))
        bcpage += shorttext + '\n'
    
    # Additional Resources section (keyword links)
    domain_status = domain_data.get('status')
    # Convert to string for comparison (handles both int and str from DB)
    domain_status_str = str(domain_status) if domain_status is not None else ''
    if domain_status_str in ['1', '2', '8', '10']:
        links_sql = """
            SELECT d.*, b.restitle, b.resshorttext, b.resfulltext, b.linkouturl, b.resname, b.resaddress, b.resphone, 
                   l.linkformat, l.deeplink, l.relevant, b.id AS bubblefeedid, b.title, b.categoryid,
                   s.servicetype AS servicename, s.price, d.servicetype,
                   bc.category AS bubblecat, bc.bubblefeedid AS bubblecatid,
                   c.category AS subcat,
                   mc.maincategories_name AS maincat,
                   d.showtagsonbusinesscollective, d.usewebsitereferencetitles
            FROM bwp_link_placement l
            LEFT JOIN bwp_domains d ON d.id = l.domainid
            LEFT JOIN bwp_services s ON d.servicetype = s.id
            LEFT JOIN bwp_bubblefeed b ON b.id = l.bubblefeedid
            LEFT JOIN bwp_bubblefeedcategory bc ON bc.id = b.categoryid
            LEFT JOIN bwp_domain_category c ON c.id = d.domain_category
            LEFT JOIN bwp_maincategories mc ON mc.maincategories_id = c.parent_catid
            WHERE l.showondomainid = %s
            AND l.showonpgid = %s
            AND l.deleted != 1
            AND l.linkformat = 'keyword'
            AND d.deleted != 1
            AND l.showondomainid NOT IN (SELECT domain_id FROM bwp_domains_disabled WHERE disabled_domain_id = d.id)
            AND d.domainip != %s
            ORDER BY l.relevant DESC
        """
        links = db.fetch_all(links_sql, (domainid, res['id'], domain_data.get('domainip', '')))
        
        if links:
            bcpage += '<div class="seo-automation-spacer"></div>\n'
            bcpage += '<h3 style="text-align:left;font-size:22px;font-weight:bold;">Additional Resources:</h3>\n'
            bcpage += '<div class="seo-automation-tag-container" style="border-bottom:0px solid black; border-top:0px solid black;;height:10px;"></div>\n'
            bcpage += '<div class="seo-automation-spacer"></div>\n'
            
            # Process each link
            for link in links:
                # Get link settings
                link_settings_sql = "SELECT * FROM bwp_domain_settings WHERE domainid = %s"
                link_settings = db.fetch_row(link_settings_sql, (link['id'],))
                if not link_settings:
                    db.execute("INSERT INTO bwp_domain_settings SET domainid = %s", (link['id'],))
                    link_settings = db.fetch_row(link_settings_sql, (link['id'],))
                
                # Build link domain URLs
                if link_settings.get('usedurl') == 1 and link.get('domain_url'):
                    linkdomain = link['domain_url'].rstrip('/')
                else:
                    if link.get('ishttps') == 1:
                        lprfx = 'https://'
                    else:
                        lprfx = 'http://'
                    if link.get('usewww') == 1:
                        linkdomain = lprfx + 'www.' + link['domain_name']
                    else:
                        linkdomain = lprfx + link['domain_name']
                
                linkdomainalone = linkdomain
                if link.get('ishttps') == 1:
                    lprfx = 'https://'
                else:
                    lprfx = 'http://'
                if link.get('usewww') == 1:
                    linkalone = lprfx + 'www.' + link['domain_name'] + '/'
                else:
                    linkalone = lprfx + link['domain_name'] + '/'
                
                if link.get('servicetype') == 370:
                    linkdomainalone = linkdomain + '/'
                
                bcdomain = link['domain_name'].split('.')
                bcvardomain = bcdomain[0] if bcdomain else ''
                
                bcpage += '<div class="seo-automation-container">\n'
                
                # Determine link URL
                haslinks_sql = "SELECT count(id) FROM bwp_link_placement WHERE deleted != 1 AND showondomainid = %s AND showonpgid = %s"
                haslinks = db.fetch_one(haslinks_sql, (link['id'], link.get('bubblefeedid')))
                haslinks = haslinks or 0
                
                if haslinks >= 1:
                    haslinkspg = {'restitle': link.get('restitle'), 'showonpgid': link.get('bubblefeedid'), 'bubblefeedid': link.get('bubblefeedid')}
                else:
                    haslinkspg_sql = """
                        SELECT l.id, l.showonpgid, b.restitle, b.id AS bubblefeedid 
                        FROM bwp_link_placement l 
                        LEFT JOIN bwp_bubblefeed b ON b.id = l.showonpgid AND b.deleted != 1 
                        WHERE l.deleted != 1 AND b.restitle <> '' AND l.showondomainid = %s 
                        ORDER BY RAND() LIMIT 1
                    """
                    haslinkspg = db.fetch_row(haslinkspg_sql, (link['id'],))
                    if not haslinkspg:
                        haslinkspg = {}
                
                # Build link URL - match PHP logic exactly
                # PHP line 322-376: Complex conditional logic for link URL building
                haslinkspg_count = haslinks if haslinks else 0
                
                if haslinkspg_count > 0 and link.get('wp_plugin') != 1 and link.get('servicetype') == 356 and link.get('status') in ['2', '10']:
                    # PHP line 322-324: CodeURL for non-WP plugin with servicetype 356
                    # Simplified CodeURL - would need full implementation
                    linkurl = linkdomain + '/?Action=2&k=' + seo_slug(seo_filter_text_custom(haslinkspg.get('restitle', '')))
                elif haslinkspg_count > 0 and link.get('wp_plugin') == 1 and link.get('servicetype') == 356 and link.get('status') in ['2', '10']:
                    # PHP line 326-331: WP plugin with servicetype 356
                    if is_bron(link.get('servicetype')):
                        linkurl = linkdomain + '/' + str(haslinkspg.get('showonpgid', '')) + 'bc/'
                    else:
                        linkurl = linkdomain + '/' + seo_slug(seo_filter_text_custom(haslinkspg.get('restitle', ''))) + '-' + str(haslinkspg.get('showonpgid', '')) + 'bc/'
                elif len(link.get('linkouturl', '')) > 5 and link.get('status') in ['2', '10'] and (not is_seom(link.get('servicetype')) or is_bron(link.get('servicetype'))):
                    # PHP line 333: linkouturl if NOT SEOM OR if BRON
                    linkurl = link['linkouturl'].strip()
                elif link.get('skipfeedchecker') == 1:
                    # PHP line 337-340
                    linkurl = linkdomainalone
                elif not link.get('bubblecat') and link.get('wp_plugin') == 1 and (len(link.get('resfulltext', '')) >= 50 or len(link.get('resshorttext', '')) >= 50) and link.get('status') in ['2', '10']:
                    # PHP line 342-344: WP plugin without bubblecat
                    import html
                    slug_text = seo_text_custom(link.get('restitle', ''))
                    slug_text = html.unescape(slug_text)
                    slug_text = to_ascii(slug_text)
                    slug_text = slug_text.lower()
                    slug_text = slug_text.replace(' ', '-')
                    linkurl = linkdomain + '/' + slug_text + '-' + str(link.get('bubblefeedid', '')) + '/'
                elif link.get('wp_plugin') == 1 and (len(link.get('resfulltext', '')) >= 50 or len(link.get('resshorttext', '')) >= 50) and link.get('status') in ['2', '10']:
                    # PHP line 346-348: WP plugin with bubblecat
                    import html
                    slug_text = seo_text_custom(link.get('bubblecat', ''))
                    slug_text = html.unescape(slug_text)
                    slug_text = to_ascii(slug_text)
                    slug_text = slug_text.lower()
                    slug_text = slug_text.replace(' ', '-')
                    linkurl = linkdomain + '/' + slug_text + '-' + str(link.get('bubblecatid', '')) + '/'
                elif not link.get('bubblecat') and link.get('wp_plugin') != 1 and (len(link.get('resfulltext', '')) >= 50 or len(link.get('resshorttext', '')) >= 50) and link.get('status') in ['2', '10']:
                    # PHP line 350-355: Non-WP plugin without bubblecat
                    if link.get('script_version', 0) >= 3 and link.get('wp_plugin') != 1 and link.get('iswin') != 1 and link.get('usepurl') != 0:
                        linkurl = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(link.get('restitle', ''))) + '/' + str(link.get('bubblefeedid', '')) + '/'
                    else:
                        # CodeURL equivalent - simplified
                        linkurl = linkdomain + '/?Action=1&k=' + seo_slug(seo_filter_text_custom(link.get('restitle', ''))) + '&PageID=' + str(link.get('bubblefeedid', ''))
                elif link.get('wp_plugin') != 1 and link.get('status') in ['2', '10']:
                    # PHP line 357-362: Non-WP plugin with bubblecat
                    if link.get('script_version', 0) >= 3 and link.get('wp_plugin') != 1 and link.get('iswin') != 1 and link.get('usepurl') != 0:
                        linkurl = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(link.get('bubblecat', ''))) + '/' + str(link.get('bubblecatid', '')) + '/'
                    else:
                        # CodeURL equivalent - simplified
                        linkurl = linkdomain + '/?Action=1&k=' + seo_slug(seo_filter_text_custom(link.get('restitle', ''))) + '&PageID=' + str(link.get('bubblefeedid', ''))
                else:
                    # PHP line 372-375: Default fallback
                    linkurl = linkalone
                
                follow = ' rel="nofollow"' if link.get('forceinboundnofollow') == 1 else ''
                
                # PHP line 410-411: moneynofollow (empty string in this case)
                moneynofollow = ''
                
                # Build title
                if link.get('title'):
                    stitle = clean_title(seo_filter_text_custom(link['title']))
                else:
                    stitle = clean_title(seo_filter_text_custom(link.get('restitle', '')))
                
                bcpage += f'<h2 class="h2"><a{moneynofollow} title="{stitle}" href="{linkurl}" style="text-align:left;" target="_blank"{follow}>{stitle}</a></h2>\n'
                
                # Support links for SEOM/BRON services
                # PHP line 415-447: Check if SEOM/BRON and bubblefeedid exists
                servicetype_val = link.get('servicetype')
                # Convert to int if it's a string or None
                if servicetype_val is not None:
                    try:
                        servicetype_val = int(servicetype_val)
                    except (ValueError, TypeError):
                        servicetype_val = None
                bubblefeedid_val = link.get('bubblefeedid')
                if (is_seom(servicetype_val) or is_bron(servicetype_val)) and bubblefeedid_val:
                    # PHP line 417: Query doesn't filter by deleted != 1
                    support_sql = """
                        SELECT id, restitle FROM bwp_bubblefeedsupport 
                        WHERE bubblefeedid = %s AND LENGTH(resfulltext) > 300
                    """
                    supps = db.fetch_all(support_sql, (bubblefeedid_val,))
                    if supps:
                        tsups = ''
                        for supp in supps:
                            suppurl = ''
                            if link.get('wp_plugin') != 1 and link.get('status') in ['2', '10', '8']:
                                # Build suppurl for non-WP plugin
                                if link.get('script_version', 0) >= 3 and link.get('wp_plugin') != 1 and link.get('iswin') != 1 and link.get('usepurl') != 0:
                                    suppurl = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(supp['restitle'])) + '/' + str(supp['id']) + '/'
                                else:
                                    # CodeURL equivalent - simplified
                                    suppurl = linkdomain + '/?Action=1&k=' + seo_slug(seo_filter_text_custom(supp['restitle'])) + '&PageID=' + str(supp['id'])
                            elif link.get('wp_plugin') == 1 and link.get('status') in ['2', '10']:
                                # Use toAscii(html_entity_decode(seo_text_custom(...))) for WP plugin
                                import html
                                supp_slug_text = seo_text_custom(supp['restitle'])
                                supp_slug_text = html.unescape(supp_slug_text)
                                supp_slug_text = to_ascii(supp_slug_text)
                                supp_slug_text = supp_slug_text.lower()
                                supp_slug_text = supp_slug_text.replace(' ', '-')
                                suppurl = linkdomain + '/' + supp_slug_text + '-' + str(supp['id']) + '/'
                            
                            if suppurl:
                                # PHP line 438: Use moneynofollow and custom_ucfirst_words(seo_text_custom(...)) for display
                                supp_title = custom_ucfirst_words(seo_text_custom(supp['restitle']))
                                tsups += '- <span style="font-size:12px;line-height:13px;"><strong> <a ' + moneynofollow + ' title="' + supp_title + '" href="' + suppurl + '" target="_blank"' + follow + '> ' + supp_title + ' </a> </strong></span> '
                        
                        # PHP line 443: ltrim($tsups, '-') - only remove leading dashes
                        tsups = tsups.lstrip('-')
                        # PHP line 444-447: if($tsups != '') output it
                        if tsups:
                            bcpage += tsups + '\n'
                
                # Build image URL - match PHP logic exactly
                # PHP line 386-405: Complex conditional logic for image URL
                if link.get('skipfeedchecker') == 1 and link.get('linkskipfeedchecker') != 1:
                    # PHP line 386-388
                    imageurl = linkdomainalone
                elif haslinkspg_count > 0 and link.get('wp_plugin') != 1 and link.get('status') in ['2', '10', '8']:
                    # PHP line 390-395: Non-WP plugin with haslinkspg
                    if link.get('script_version', 0) >= 3 and link.get('wp_plugin') != 1 and link.get('iswin') != 1 and link.get('usepurl') != 0:
                        imageurl = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(haslinkspg.get('restitle', ''))) + '/' + str(haslinkspg.get('bubblefeedid', '')) + 'bc/'
                    else:
                        # CodeURL equivalent - simplified
                        imageurl = linkdomain + '/?Action=2&k=' + seo_slug(seo_filter_text_custom(haslinkspg.get('restitle', '')))
                elif (haslinkspg_count > 0 or is_bron(link.get('servicetype'))) and link.get('status') in ['2', '10', '8']:
                    # PHP line 397-402: haslinkspg > 0 OR isBRON
                    if is_bron(link.get('servicetype')):
                        imageurl = linkdomain + '/' + str(haslinkspg.get('showonpgid', '')) + 'bc/'
                    else:
                        import html
                        slug_text = seo_text_custom(haslinkspg.get('restitle', ''))
                        slug_text = html.unescape(slug_text)
                        slug_text = to_ascii(slug_text)
                        slug_text = slug_text.lower()
                        slug_text = slug_text.replace(' ', '-')
                        imageurl = linkdomain + '/' + slug_text + '-' + str(haslinkspg.get('showonpgid', '')) + 'bc/'
                else:
                    # PHP line 404-405: Default fallback
                    imageurl = linkalone
                
                # Build citation container if address/name exists
                preml = 0
                map_val = 0
                stadd = ''
                cty = ''
                state = ''
                zip_code = ''
                mapurl = ''
                address = ''
                
                if (link.get('wr_address') or link.get('resaddress')) and (link.get('wr_name') or link.get('resname')):
                    preml = 1
                    address = link.get('resaddress') or link.get('wr_address', '')
                    
                    if link_settings.get('gmbframe') and len(link_settings['gmbframe']) > 10:
                        mapurl = link_settings['gmbframe']
                        map_val = 1
                        # Parse address even when gmbframe exists
                        if address:
                            addressarray = address.split(',')
                            if len(addressarray) >= 3:
                                stzipstr = addressarray[2]
                                stziparray = stzipstr.strip().split(' ')
                                if len(stziparray) == 2:
                                    stadd = addressarray[0]
                                    cty = addressarray[1]
                                    state = stziparray[0]
                                    zip_code = stziparray[1]
                                elif len(stziparray) == 3:
                                    stadd = addressarray[0].strip()
                                    cty = addressarray[1].strip()
                                    state = stziparray[0].strip()
                                    zip_code = stziparray[1].strip()
                                    zip_code += ' ' + stziparray[2].strip()
                    elif address:
                        addressarray = address.split(',')
                        if len(addressarray) == 3:
                            stzipstr = addressarray[2]
                            stziparray = stzipstr.strip().split(' ')
                            if len(stziparray) == 2:
                                stadd = addressarray[0]
                                cty = addressarray[1]
                                state = stziparray[0]
                                zip_code = stziparray[1]
                                map_val = 1
                            elif len(stziparray) == 3:
                                stadd = addressarray[0].strip()
                                cty = addressarray[1].strip()
                                state = stziparray[0].strip()
                                zip_code = stziparray[1].strip()
                                zip_code += ' ' + stziparray[2].strip()
                                map_val = 1
                            
                            if map_val == 1:
                                wr_name = link.get('resname') or link.get('wr_name', '')
                                mapurl = f'https://www.google.com/maps/embed/v1/place?key=AIzaSyDET-f-9dCENEEt8nU2MLOXluoEtrq2k5o&q={quote(wr_name)}+{quote(address.replace(",", ""))}'
                
                # Citation container is ALWAYS created when preml == 1 (PHP line 531)
                if preml == 1:
                    bcpage += '<div class="bwp_citation_conatainer">\n'
                    bcpage += '<div itemscope itemtype="http://schema.org/LocalBusiness">\n'
                    bcpage += '<div class="citation_map_container">\n'
                    
                    if map_val == 1:
                        bcpage += f'<iframe width="130" height="110" style="width:130px;height:110px;border:0;overflow:hidden;" src="{mapurl}"></iframe>\n'
                        bcpage += f'<img itemprop="image" src="//imagehosting.space/feed/pageimage.php?domain={link["domain_name"]}" alt="{link["domain_name"]}" style="display:none !important;">\n'
                    else:
                        bcpage += f'<a href="{imageurl}" target="_blank"{follow}><img itemprop="image" src="//imagehosting.space/feed/pageimage.php?domain={link["domain_name"]}" alt="{link["domain_name"]}" style="width:130px !important;height:110px;"></a>\n'
                    
                    bcpage += '</div>\n'
                    
                    wr_name = link.get('resname') or link.get('wr_name', '')
                    bcpage += f'<span itemprop="name" style="font-size:12px;line-height:13px;"><strong>{wr_name}</strong></span><br>\n'
                    
                    # Address is only shown when address exists and map == 1 (PHP line 559)
                    if address and map_val == 1 and stadd:
                        bcpage += '<div itemprop="address" itemscope itemtype="http://schema.org/PostalAddress">\n'
                        bcpage += f'<span style="font-size:12px;line-height:13px;" itemprop="streetAddress">{stadd}</span><br>\n'
                        bcpage += f'<span style="font-size:12px;line-height:13px;" itemprop="addressLocality">{cty}</span> '
                        bcpage += f'<span style="font-size:12px;line-height:13px;" itemprop="addressRegion">{state}</span> '
                        bcpage += f'<span style="font-size:12px;line-height:13px;" itemprop="postalCode">{zip_code}</span>\n'
                        bcpage += f'<span style="font-size:12px;line-height:13px;display:none;" itemprop="addressCountry">{link.get("domain_country", "")}</span><br>\n'
                    
                    if link.get('wr_phone') or link.get('resphone'):
                        phon = link.get('resphone') or link.get('wr_phone', '')
                        bcpage += f'<span style="font-size:12px;line-height:13px;" itemprop="telephone">{phon}<br>\n'
                    
                    bcpage += f'<a style="font-size:12px;line-height:13px;" itemprop="url" href="{linkalone}">{link["domain_name"]}</a></span><br>\n'
                    
                    if address and map_val == 1:
                        bcpage += '</div>\n'
                    
                    # Social media icons
                    if (link.get('wr_googleplus') or link.get('wr_facebook') or link.get('wr_twitter') or 
                        link.get('wr_linkedin') or link.get('wr_yelp') or link.get('wr_bing') or link.get('wr_yahoo')):
                        bcpage += '<div class="seo-automation-space"></div>\n'
                        alttxt = seo_filter_text_custom(link.get('restitle', ''))
                        bcpage += '<div class="related-art-social">\n'
                        
                        # Add all social icons
                        if link.get('wr_facebook'):
                            urlf = link['wr_facebook']
                            if 'http' in urlf:
                                urlf = urlf.replace('http:', 'https:')
                            elif urlf.startswith('/'):
                                urlf = 'https://www.facebook.com' + urlf
                            else:
                                urlf = 'https://www.facebook.com/' + urlf
                            bcpage += f'<a href="{urlf}" title="{alttxt} - Follow us on Facebook" target="_blank"><img src="//imagehosting.space/images/fbfavicon.ico" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_twitter'):
                            urlt = link['wr_twitter']
                            if 'http' in urlt:
                                urlt = urlt.replace('http:', 'https:')
                            elif urlt.startswith('/'):
                                urlt = 'https://twitter.com' + urlt
                            else:
                                urlt = 'https://twitter.com/' + urlt
                            bcpage += f'<a href="{urlt}" title="{alttxt} - Follow us on Twitter" target="_blank"><img src="//imagehosting.space/images/twitfavicon.ico" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_linkedin'):
                            urll = link['wr_linkedin']
                            if 'http' in urll:
                                urll = urll.replace('http:', 'https:')
                            elif urll.startswith('/'):
                                urll = 'https://www.linkedin.com/pub' + urll
                            else:
                                urll = 'https://www.linkedin.com/pub/' + urll
                            bcpage += f'<a href="{urll}" title="{alttxt} - Follow us on LinkedIn" target="_blank"><img src="//imagehosting.space/images/linkfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_googleplus'):
                            urlg = link['wr_googleplus']
                            if 'http' in urlg:
                                urlg = urlg.replace('http:', 'https:')
                            elif urlg.startswith('/'):
                                urlg = 'https://plus.google.com' + urlg
                            else:
                                urlg = 'https://plus.google.com/' + urlg
                            bcpage += f'<a href="{urlg}" title="{alttxt} - Find us on Google" target="_blank"><img src="//imagehosting.space/images/maps15_bnuw3a_32dp.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_yelp'):
                            urly = link['wr_yelp']
                            bcpage += f'<a href="{urly}" title="{alttxt} - Follow us on Yelp" target="_blank"><img src="//imagehosting.space/images/yelpfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_bing'):
                            urly = link['wr_bing']
                            bcpage += f'<a href="{urly}" title="{alttxt} - Find us on Bing" target="_blank"><img src="//imagehosting.space/images/bingfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_yahoo'):
                            urly = link['wr_yahoo']
                            bcpage += f'<a href="{urly}" title="{alttxt} - Find us on Yahoo" target="_blank"><img src="//imagehosting.space/images/yahoofavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        bcpage += '</div>\n'
                    
                    if link_settings.get('blogUrl') and len(link_settings['blogUrl']) > 10:
                        bcpage += f' <a target="_blank" href="{link_settings["blogUrl"]}">Blog</a>  '
                    if link_settings.get('faqUrl') and len(link_settings['faqUrl']) > 10:
                        bcpage += f' <a target="_blank" href="{link_settings["faqUrl"]}">FAQ</a> '
                    
                    bcpage += '</div>\n'
                    bcpage += '</div>\n'
                else:
                    # No address - just image
                    bcpage += '<div class="snapshot-container" style="margin-left:20px !important;">\n'
                    bcpage += f'<a href="{imageurl}" target="_blank"{follow}><img src="//imagehosting.space/feed/pageimage.php?domain={link["domain_name"]}" alt="{link["domain_name"]}" style="width:130px !important;height:110px;"></a>\n'
                    if link_settings.get('blogUrl') and len(link_settings['blogUrl']) > 10:
                        bcpage += f' <a target="_blank" href="{link_settings["blogUrl"]}">Blog</a>  '
                    if link_settings.get('faqUrl') and len(link_settings['faqUrl']) > 10:
                        bcpage += f' <a target="_blank" href="{link_settings["faqUrl"]}">FAQ</a> '
                    bcpage += '</div>\n'
                
                # Build text content
                if link.get('resname'):
                    wr_name = link['resname']
                else:
                    wr_name = link.get('wr_name', '')
                
                if link.get('restitle') and not is_bron(link.get('servicetype')):
                    restextkw = seo_filter_text_custom(link['restitle'])
                elif wr_name:
                    restextkw = seo_filter_text_custom(wr_name)
                else:
                    restextkw = seo_filter_text_custom(link.get('domain_name', ''))
                
                if link.get('desc2') and not link.get('resshorttext'):
                    restext = seo_filter_text_custom(link['desc2'])
                else:
                    restext = seo_filter_text_custom(link.get('resshorttext', ''))
                
                if len(restext) < 20:
                    restext = restextkw
                
                # Trim to first 100 words (PHP trimToFirst100Words)
                words = restext.split()[:100]
                restext = ' '.join(words)
                
                # Add link to text - match PHP logic exactly
                # PHP line 714-741: Complex conditional logic for adding links to text
                addrndfeed = 0
                if map_val == 1:
                    # PHP line 714-715: map == 1
                    # Use seo_automation_add_text_link_newbc equivalent
                    restext = seo_automation_add_text_link_newbc(restext, restextkw, imageurl, follow)
                elif preml == 1:
                    # PHP line 716-717: preml == 1
                    restext = seo_automation_add_text_link_newbc(restext, restextkw, '', follow)
                elif (link.get('status') == '8' and haslinkspg_count > 1) or (addrndfeed == 1 and haslinkspg_count > 1):
                    # PHP line 718-738: Orphan link handling
                    orphan_sql = """
                        SELECT l.id, l.showonpgid, b.restitle, b.id AS bubblefeedid 
                        FROM bwp_link_placement l 
                        LEFT JOIN bwp_bubblefeed b ON b.id = l.showonpgid AND b.deleted != 1 
                        WHERE l.deleted != 1 AND b.restitle <> '' AND b.id != %s AND l.showondomainid = %s 
                        ORDER BY RAND() LIMIT 1
                    """
                    orphanlinkspg = db.fetch_row(orphan_sql, (haslinkspg.get('bubblefeedid', ''), link['id']))
                    if orphanlinkspg and link.get('wp_plugin') != 1:
                        # PHP line 721-726: Non-WP plugin orphan link
                        if link.get('script_version', 0) >= 3 and link.get('wp_plugin') != 1 and link.get('iswin') != 1 and link.get('usepurl') != 0:
                            orphlink = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(orphanlinkspg.get('restitle', ''))) + '/' + str(orphanlinkspg.get('bubblefeedid', '')) + 'bc/'
                        else:
                            # CodeURL equivalent - simplified
                            orphlink = linkdomain + '/?Action=2&k=' + seo_slug(seo_filter_text_custom(orphanlinkspg.get('restitle', '')))
                    elif orphanlinkspg and link.get('wp_plugin') == 1:
                        # PHP line 728-733: WP plugin orphan link
                        if is_bron(link.get('servicetype')):
                            orphlink = linkdomain + '/' + str(orphanlinkspg.get('showonpgid', '')) + 'bc/'
                        else:
                            import html
                            slug_text = seo_text_custom(orphanlinkspg.get('restitle', ''))
                            slug_text = html.unescape(slug_text)
                            slug_text = to_ascii(slug_text)
                            slug_text = slug_text.lower()
                            slug_text = slug_text.replace(' ', '-')
                            orphlink = linkdomain + '/' + slug_text + '-' + str(orphanlinkspg.get('showonpgid', '')) + 'bc/'
                    else:
                        orphlink = linkalone
                    restext = seo_automation_add_text_link_newbc(restext, restextkw, orphlink, follow)
                else:
                    # PHP line 740-741: Default fallback
                    restext = seo_automation_add_text_link_newbc(restext, restextkw, linkalone, follow)
                
                bcpage += restext + '\n'
                
                # Social media if no address
                if preml == 0:
                    if (link.get('wr_googleplus') or link.get('wr_facebook') or link.get('wr_twitter') or 
                        link.get('wr_linkedin') or link.get('wr_yelp') or link.get('wr_bing') or link.get('wr_yahoo')):
                        bcpage += '<div style="height:1px;"></div>\n'
                        alttxt = seo_filter_text_custom(link.get('restitle', ''))
                        bcpage += '<div class="related-art-social" style="float:left;">\n'
                        
                        # Add all social icons
                        if link.get('wr_facebook'):
                            urlf = link['wr_facebook']
                            if 'http' in urlf:
                                urlf = urlf.replace('http:', 'https:')
                            elif urlf.startswith('/'):
                                urlf = 'https://www.facebook.com' + urlf
                            else:
                                urlf = 'https://www.facebook.com/' + urlf
                            bcpage += f'<a href="{urlf}" title="{alttxt} - Follow us on Facebook" target="_blank"><img src="//imagehosting.space/images/fbfavicon.ico" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_twitter'):
                            urlt = link['wr_twitter']
                            if 'http' in urlt:
                                urlt = urlt.replace('http:', 'https:')
                            elif urlt.startswith('/'):
                                urlt = 'https://twitter.com' + urlt
                            else:
                                urlt = 'https://twitter.com/' + urlt
                            bcpage += f'<a href="{urlt}" title="{alttxt} - Follow us on Twitter" target="_blank"><img src="//imagehosting.space/images/twitfavicon.ico" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_linkedin'):
                            urll = link['wr_linkedin']
                            if 'http' in urll:
                                urll = urll.replace('http:', 'https:')
                            elif urll.startswith('/'):
                                urll = 'https://www.linkedin.com/pub' + urll
                            else:
                                urll = 'https://www.linkedin.com/pub/' + urll
                            bcpage += f'<a href="{urll}" title="{alttxt} - Follow us on LinkedIn" target="_blank"><img src="//imagehosting.space/images/linkfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_googleplus'):
                            urlg = link['wr_googleplus']
                            if 'http' in urlg:
                                urlg = urlg.replace('http:', 'https:')
                            elif urlg.startswith('/'):
                                urlg = 'https://plus.google.com' + urlg
                            else:
                                urlg = 'https://plus.google.com/' + urlg
                            bcpage += f'<a href="{urlg}" title="{alttxt} - Find us on Google" target="_blank"><img src="//imagehosting.space/images/maps15_bnuw3a_32dp.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_yelp'):
                            urly = link['wr_yelp']
                            bcpage += f'<a href="{urly}" title="{alttxt} - Follow us on Yelp" target="_blank"><img src="//imagehosting.space/images/yelpfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_bing'):
                            urly = link['wr_bing']
                            bcpage += f'<a href="{urly}" title="{alttxt} - Find us on Bing" target="_blank"><img src="//imagehosting.space/images/bingfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_yahoo'):
                            urly = link['wr_yahoo']
                            bcpage += f'<a href="{urly}" title="{alttxt} - Find us on Yahoo" target="_blank"><img src="//imagehosting.space/images/yahoofavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        bcpage += '</div>\n'
                
                bcpage += '</div><div class="seo-automation-spacer"></div>\n'
    
    # Drip content links section
    linksdc_sql = """
        SELECT d.*, b.id AS bubbafeedid, b.bubblefeedid, b.restitle, b.bubbatitle, b.resshorttext, b.resfulltext, 
               b.linkouturl, b.resaddress, b.resphone, l.linkformat, l.deeplink, l.relevant,
               s.servicetype AS servicename, s.price,
               c.category AS subcat,
               mc.maincategories_name AS maincat,
               d.showtagsonbusinesscollective, d.usewebsitereferencetitles
        FROM bwp_link_placement l
        LEFT JOIN bwp_domains d ON d.id = l.domainid
        LEFT JOIN bwp_services s ON d.servicetype = s.id
        LEFT JOIN bwp_bubbafeed b ON b.id = l.bubblefeedid
        LEFT JOIN bwp_bubblefeed bl ON bl.id = b.bubblefeedid
        LEFT JOIN bwp_domain_category c ON c.id = d.domain_category
        LEFT JOIN bwp_maincategories mc ON mc.maincategories_id = c.parent_catid
        WHERE l.showondomainid = %s
        AND l.showonpgid = %s
        AND l.deleted != 1
        AND d.deleted != 1
        AND b.deleted != 1
        AND bl.deleted != 1
        AND l.linkformat = 'dripcontent'
        AND l.showondomainid NOT IN (SELECT domain_id FROM bwp_domains_disabled WHERE disabled_domain_id = d.id)
        AND d.domainip != %s
        ORDER BY l.relevant DESC
    """
    linksdc = db.fetch_all(linksdc_sql, (domainid, res['id'], domain_data.get('domainip', '')))
    
    if linksdc:
        for linkdc in linksdc:
            # Build link domain
            if linkdc.get('ishttps') == 1:
                lprfx = 'https://'
            else:
                lprfx = 'http://'
            if linkdc.get('usewww') == 1:
                linkdomain = lprfx + 'www.' + linkdc['domain_name']
            else:
                linkdomain = lprfx + linkdc['domain_name']
            
            linkdomainalone = linkdomain
            if linkdc.get('servicetype') == 370:
                linkdomainalone = linkdomain + '/'
            
            bcdomain = linkdc['domain_name'].split('.')
            bcvardomain = bcdomain[0] if bcdomain else ''
            
            bcpage += '<div class="seo-automation-container">\n'
            
            # Build link URL - match PHP logic exactly
            # PHP line 895-927: Complex conditional logic for drip content link URL
            if len(linkdc.get('linkouturl', '')) > 5 and linkdc.get('status') in ['2', '10']:
                # PHP line 895-897
                linkurl = linkdc['linkouturl'].strip()
            elif linkdc.get('skipfeedchecker') == 1 and linkdc.get('linkskipfeedchecker') != 1:
                # PHP line 899-902
                linkurl = linkdomainalone
            elif linkdc.get('wp_plugin') == 1 and len(linkdc.get('resfulltext', '')) >= 300:
                # PHP line 904-906: Use toAscii(html_entity_decode(seo_text_custom(...)))
                import html
                slug_text = seo_text_custom(linkdc.get('bubbatitle', ''))
                slug_text = html.unescape(slug_text)
                slug_text = to_ascii(slug_text)
                slug_text = slug_text.lower()
                slug_text = slug_text.replace(' ', '-')
                linkurl = linkdomain + '/' + slug_text + '-' + str(linkdc.get('bubbafeedid', '')) + 'dc'
            elif linkdc.get('wp_plugin') != 1 and len(linkdc.get('resfulltext', '')) >= 50 and linkdc.get('status') in ['2', '10']:
                # PHP line 908-913: Non-WP plugin
                if linkdc.get('script_version', 0) > 3.2 and linkdc.get('wp_plugin') != 1 and linkdc.get('iswin') != 1 and linkdc.get('usepurl') != 0:
                    linkurl = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(linkdc.get('bubbatitle', ''))) + '/' + str(linkdc.get('bubbafeedid', '')) + 'dc'
                else:
                    # CodeURL equivalent - simplified
                    linkurl = linkdomain + '/?Action=3&k=' + seo_slug(seo_filter_text_custom(linkdc.get('bubbatitle', ''))) + '&PageID=' + str(linkdc.get('bubbafeedid', ''))
            else:
                # PHP line 924-926: Default fallback
                linkurl = linkdomainalone
            
            follow = ' rel="nofollow"' if linkdc.get('forceinboundnofollow') == 1 else ''
            stitle = clean_title(seo_filter_text_custom(linkdc.get('bubbatitle', '')))
            
            bcpage += f'<h2 class="h2"><a title="{stitle}" href="{linkurl}" style="text-align:left;" target="_blank"{follow}>{stitle}</a></h2>\n'
            
            # Build image URL - match PHP logic exactly
            # PHP line 934-950: Complex conditional logic for drip content image URL
            haslinks_dc_sql = "SELECT count(id) FROM bwp_link_placement WHERE deleted != 1 AND showondomainid = %s AND showonpgid = %s"
            haslinks_dc = db.fetch_one(haslinks_dc_sql, (linkdc['id'], linkdc.get('bubblefeedid')))
            haslinks_dc = haslinks_dc or 0
            
            if haslinks_dc >= 1:
                haslinkspg_dc = {'restitle': linkdc.get('restitle'), 'showonpgid': linkdc.get('bubblefeedid'), 'bubblefeedid': linkdc.get('bubblefeedid')}
            else:
                haslinkspg_dc_sql = """
                    SELECT l.id, l.showonpgid, b.restitle, b.id AS bubblefeedid 
                    FROM bwp_link_placement l 
                    LEFT JOIN bwp_bubblefeed b ON b.id = l.showonpgid AND b.deleted != 1 
                    WHERE l.deleted != 1 AND b.restitle <> '' AND l.showondomainid = %s 
                    ORDER BY RAND() LIMIT 1
                """
                haslinkspg_dc = db.fetch_row(haslinkspg_dc_sql, (linkdc['id'],))
                if not haslinkspg_dc:
                    haslinkspg_dc = {}
            
            haslinkspg_dc_count = haslinks_dc if haslinks_dc else 0
            
            if linkdc.get('skipfeedchecker') == 1 and linkdc.get('linkskipfeedchecker') != 1:
                # PHP line 934-936
                imageurl = linkdomainalone
            elif haslinkspg_dc_count > 0 and linkdc.get('wp_plugin') != 1 and linkdc.get('status') in ['2', '10', '8']:
                # PHP line 938-943: Non-WP plugin with haslinkspg
                if linkdc.get('script_version', 0) > 3.2 and linkdc.get('wp_plugin') != 1 and linkdc.get('iswin') != 1 and linkdc.get('usepurl') != 0:
                    imageurl = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(haslinkspg_dc.get('restitle', ''))) + '/' + str(haslinkspg_dc.get('bubblefeedid', '')) + 'bc/'
                else:
                    # CodeURL equivalent - simplified
                    imageurl = linkdomain + '/?Action=2&k=' + seo_slug(seo_filter_text_custom(haslinkspg_dc.get('restitle', '')))
            elif haslinkspg_dc_count > 0 and linkdc.get('wp_plugin') == 1 and linkdc.get('status') in ['2', '10', '8']:
                # PHP line 945-947: WP plugin with haslinkspg - use toAscii(html_entity_decode(seo_text_custom(...)))
                import html
                slug_text = seo_text_custom(haslinkspg_dc.get('restitle', ''))
                slug_text = html.unescape(slug_text)
                slug_text = to_ascii(slug_text)
                slug_text = slug_text.lower()
                slug_text = slug_text.replace(' ', '-')
                imageurl = linkdomain + '/' + slug_text + '-' + str(haslinkspg_dc.get('showonpgid', '')) + 'bc/'
            else:
                # PHP line 949-950: Default fallback
                imageurl = linkdomainalone
            
            # Build text content
            wr_name = linkdc.get('wr_name', '')
            if linkdc.get('restitle'):
                restextkw = seo_filter_text_custom(linkdc['restitle'])
            elif wr_name:
                restextkw = seo_filter_text_custom(wr_name)
            else:
                restextkw = seo_filter_text_custom(linkdc.get('domain_name', ''))
            
            # Get bubbatext
            bubbatext = linkdc.get('resfulltext', '')
            if bubbatext:
                bubbatext = html.unescape(bubbatext)
                # Strip tags except img (PHP: strip_tags with '<img>' allowed)
                bubbatext = re.sub(r'<(?!img\b)[^>]+>', '', bubbatext)
                # Shorten to 75 characters (PHP: bwp_shorten_string($bubbatext,75))
                if len(bubbatext) > 75:
                    bubbatext = bubbatext[:75].rsplit(' ', 1)[0] + '...'
                # Replace gallery URLs
                bubbatext = bubbatext.replace('//gallery.imagehosting.space/gallery/', '//gallery.imagehosting.space/thumbs/')
                # Wrap images in links (PHP: preg_replace pattern)
                bubbatext = re.sub(r'(?<!<a\s[^>]*>)(<img[^>]+>)(?!</a>)', f'<a href="{imageurl}">\\1</a>', bubbatext)
                # Add keyword link using seo_automation_add_text_link_newbc
                # PHP line 1215: Uses seo_automation_add_text_link_newbc
                bubbatext = seo_automation_add_text_link_newbc(bubbatext, restextkw, linkurl, follow)
            
            bcpage += bubbatext + '\n'
            
            # Social media if no address
            if (linkdc.get('wr_googleplus') or linkdc.get('wr_facebook') or linkdc.get('wr_twitter') or 
                linkdc.get('wr_linkedin') or linkdc.get('wr_yelp') or linkdc.get('wr_bing') or linkdc.get('wr_yahoo')):
                bcpage += '<div style="height:1px;"></div>\n'
                alttxt = seo_filter_text_custom(linkdc.get('restitle', ''))
                bcpage += '<div class="related-art-social" style="float:left;">\n'
                
                # Add all social icons
                if linkdc.get('wr_facebook'):
                    urlf = linkdc['wr_facebook']
                    if 'http' in urlf:
                        urlf = urlf.replace('http:', 'https:')
                    elif urlf.startswith('/'):
                        urlf = 'https://www.facebook.com' + urlf
                    else:
                        urlf = 'https://www.facebook.com/' + urlf
                    bcpage += f'<a href="{urlf}" title="{alttxt} - Follow us on Facebook" target="_blank"><img src="//imagehosting.space/images/fbfavicon.ico" width="16" alt="{alttxt}"></a>'
                
                if linkdc.get('wr_twitter'):
                    urlt = linkdc['wr_twitter']
                    if 'http' in urlt:
                        urlt = urlt.replace('http:', 'https:')
                    elif urlt.startswith('/'):
                        urlt = 'https://twitter.com' + urlt
                    else:
                        urlt = 'https://twitter.com/' + urlt
                    bcpage += f'<a href="{urlt}" title="{alttxt} - Follow us on Twitter" target="_blank"><img src="//imagehosting.space/images/twitfavicon.ico" width="16" alt="{alttxt}"></a>'
                
                if linkdc.get('wr_linkedin'):
                    urll = linkdc['wr_linkedin']
                    if 'http' in urll:
                        urll = urll.replace('http:', 'https:')
                    elif urll.startswith('/'):
                        urll = 'https://www.linkedin.com/pub' + urll
                    else:
                        urll = 'https://www.linkedin.com/pub/' + urll
                    bcpage += f'<a href="{urll}" title="{alttxt} - Follow us on LinkedIn" target="_blank"><img src="//imagehosting.space/images/linkfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                
                if linkdc.get('wr_googleplus'):
                    urlg = linkdc['wr_googleplus']
                    if 'http' in urlg:
                        urlg = urlg.replace('http:', 'https:')
                    elif urlg.startswith('/'):
                        urlg = 'https://plus.google.com' + urlg
                    else:
                        urlg = 'https://plus.google.com/' + urlg
                    bcpage += f'<a href="{urlg}" title="{alttxt} - Find us on Google" target="_blank"><img src="//imagehosting.space/images/maps15_bnuw3a_32dp.ico" border="0" width="16" alt="{alttxt}"></a>'
                
                if linkdc.get('wr_yelp'):
                    urly = linkdc['wr_yelp']
                    bcpage += f'<a href="{urly}" title="{alttxt} - Follow us on Yelp" target="_blank"><img src="//imagehosting.space/images/yelpfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                
                if linkdc.get('wr_bing'):
                    urly = linkdc['wr_bing']
                    bcpage += f'<a href="{urly}" title="{alttxt} - Find us on Bing" target="_blank"><img src="//imagehosting.space/images/bingfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                
                if linkdc.get('wr_yahoo'):
                    urly = linkdc['wr_yahoo']
                    bcpage += f'<a href="{urly}" title="{alttxt} - Find us on Yahoo" target="_blank"><img src="//imagehosting.space/images/yahoofavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                
                bcpage += '</div>\n'
            
            bcpage += '</div><div class="seo-automation-spacer"></div>\n'
    
    # Closing HTML
    bcpage += '<div class="seo-automation-spacer"></div>\n'
    bcpage += '<div class="seo-automation-tag-container" style="border-bottom:1px solid black; border-top:1px solid black;"></div>\n'
    bcpage += '<link rel="stylesheet" id="SEO_Automation_premium_0_X-css" href="https://public.imagehosting.space/external_files/premiumstyles.css" type="text/css" media="all" />\n'
    bcpage += '<div class="seo-automation-spacer"></div>\n'
    bcpage += '</div>\n'
    bcpage += '''<style>
.ngodkrbsitr-spacer{clear:both;}
.citation_map_container iframe {
	width:130px !important;
}
.vid-container iframe {
	width:100% !important;
}
</style>
'''
    
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
    import html
    wpage = '<div class="seo-automation-main-table">'
    wpage += f'<h1>{clean_title(seo_filter_text_custom(res.get("bubbatitle", "")))}</h1>'
    
    if res.get('resfulltext'):
        # Unescape HTML entities
        content = html.unescape(str(res['resfulltext']))
        wpage += f'<div class="seo-content">{content}</div>'
    
    wpage += '</div>'
    
    return wpage