from backend_patch import patch_backend
"""Search/pagination regressions at the API/provider HTML boundary."""
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
import server_fixed as s

CATEGORIES = {
    'cpu': ('113973', 'CPU', 'Intel Core i5-14600KF'),
    'mb': ('112751', '메인보드', 'ASUS B850 AM5'),
    'ram': ('112752', 'RAM 메모리', 'Samsung DDR5 16GB'),
    'storage': ('112760', 'SSD', 'Samsung 990 PRO 1TB SSD'),
    'psu': ('112777', '파워', 'MSI 850W 파워'),
    'hdd': ('1131401', 'HDD', 'Seagate 4TB HDD'),
    'gpu': ('112753', '그래픽카드', 'ASUS GeForce RTX 4070 SUPER'),
    'case': ('112775', '케이스', 'NZXT H5 Flow'),
    'software': ('223', '소프트웨어', 'Microsoft Windows 11 Home'),
}

def html_rows(kind, start, count, names=None):
    category, label, name = CATEGORIES[kind]
    rows = []
    for i in range(count):
        code = start + i + 10000
        title = names[i] if names else f'{name} SKU {code}'
        rows.append(f'''<li id="productItem{code}"><input id="productItem_categoryInfo_{code}" value="PC 주요 부품_{label}">
        <p class="prod_name"><a href="https://prod.danawa.com/info/?pcode={code}&cate={category}">{title}</a></p>
        <input id="min_price_{code}" value="{100000 + code}"><div class="spec_list"></div></li>''')
    return '<div id="productListArea"><ul>' + ''.join(rows) + '</ul></div>'

class ProductBrowsingTests(unittest.TestCase):
    def setUp(self):
        s.MARKET_BROWSE_CACHE.clear()
        getattr(s, 'MARKET_SEARCH_CACHE', {}).clear()
        self.saved = patch_backend(s, 'saved_products', return_value=[])
        self.persist = patch_backend(s, 'remember_products')
        self.saved.start(); self.persist.start()
        self.addCleanup(self.saved.stop); self.addCleanup(self.persist.stop)

    def provider(self, kind, available=121):
        def fetch(url, provider, timeout=8):
            args = parse_qs(urlparse(url).query)
            page = int(args['page'][0]); size = int(args['limit'][0])
            start = (page - 1) * size
            return html_rows(kind, start, max(0, min(size, available - start)))
        return fetch

    def test_category_pages_fill_fifty_after_provider_pagination(self):
        for kind in ['mb', 'cpu', 'ram', 'storage', 'psu', 'hdd', 'gpu']:
            with self.subTest(kind=kind), patch_backend(s, '_market_fetch_html', side_effect=self.provider(kind)) as fetch:
                first = s.market_products_response(kind, source='danawa', limit=50)
                second = s.market_products_response(kind, source='danawa', limit=50, page=2)
                self.assertEqual(50, len(first['items']))
                self.assertEqual(50, len(second['items']))
                self.assertFalse({p['id'] for p in first['items']} & {p['id'] for p in second['items']})
                self.assertTrue(first['has_more'])
                self.assertGreaterEqual(fetch.call_count, 3)

    def test_refresh_does_not_shift_an_existing_cursor(self):
        with patch_backend(s, '_market_fetch_html', side_effect=self.provider('mb')):
            first = s.market_products_response('mb', source='danawa', limit=50)
            s.market_products_response('mb', source='danawa', limit=50, refresh=True)
            second = s.market_products_response('mb', source='danawa', limit=50, page=2, cursor=first['cursor'])
        self.assertEqual(first['cursor'], second['cursor'])
        self.assertFalse({p['id'] for p in first['items']} & {p['id'] for p in second['items']})

    def test_compuzone_fifty_pages_advance_fixed_twenty_row_offsets(self):
        offsets = []
        def fetch(url, provider, timeout=8):
            args = parse_qs(urlparse(url).query)
            start = int(args['StartNum'][0]); offsets.append(start)
            self.assertEqual('20', args['PageCount'][0])
            rows = []
            for code in range(start + 10000, min(start + 10020, 10121)):
                rows.append(f'<li id="li-pno-{code}"><a class="prdTxt" href="../product/product_detail.htm?ProductNo={code}&MediumDivNo=1013">ASUS B850 AM5 SKU {code}</a><div class="prd_price" data-price="200000"></div></li>')
            return '<ul>' + ''.join(rows) + '</ul>'
        with patch_backend(s, '_market_fetch_html', side_effect=fetch):
            first = s.market_products_response('mb', source='compuzone', limit=50)
            second = s.market_products_response('mb', source='compuzone', limit=50, page=2, cursor=first['cursor'])
        self.assertEqual((50,50), (len(first['items']),len(second['items'])))
        self.assertEqual([0,20,40,60,80], offsets)
        self.assertFalse({r['id'] for r in first['items']} & {r['id'] for r in second['items']})

    def test_live_and_saved_alias_ids_deduplicate_by_retail_sku(self):
        old = dict(id='old-alias',name='ASUS B850 AM5',price=999000,price_status='cached',url='https://prod.danawa.com/info/?pcode=10000&cate=112751')
        with patch_backend(s, 'saved_products', return_value=[old]), patch_backend(s, '_market_fetch_html', side_effect=self.provider('mb',17)):
            result = s.market_products_response('mb', source='danawa',limit=50)
        self.assertEqual(17,len(result['items']))
        self.assertNotIn('old-alias',[r['id'] for r in result['items']])
        self.assertNotIn(999000,[r['price'] for r in result['items']])

    def test_fewer_than_fifty_returns_all_and_stops(self):
        with patch_backend(s, '_market_fetch_html', side_effect=self.provider('mb', 17)):
            result = s.market_products_response('mb', source='danawa', limit=50)
        self.assertEqual(17, len(result['items']))
        self.assertFalse(result['has_more'])

    def test_series_queries_accept_whole_generation_and_exclude_workstations(self):
        pairs = [('RTX 50', ['RTX 5090', 'RTX 5080', 'RTX 5070 Ti', 'RTX 5070', 'RTX 5060 Ti', 'RTX 5060', 'RTX 5050']),
                 ('RTX 40', ['RTX 4090', 'RTX 4080 SUPER', 'RTX 4070 SUPER', 'RTX 4060 Ti']),
                 ('RTX 30', ['RTX 3090', 'RTX 3080', 'RTX 3070', 'RTX 3060 Ti']),
                 ('RX 9000', ['RX 9070 XT', 'RX 9060 XT']), ('RX 7000', ['RX 7900 XTX', 'RX 7800 XT', 'RX 7600']),
                 ('RX 6000', ['RX 6950 XT', 'RX 6800 XT', 'RX 6600'])]
        for series, models in pairs:
            names = [f'ASUS {model} 16GB' for model in models] + ['NVIDIA RTX 4500 Ada', 'ASUS RTX 2080']
            with self.subTest(series=series), patch_backend(s, '_market_fetch_html', return_value=html_rows('gpu', 0, len(names), names)):
                result = s.market_products_response('gpu', series, source='danawa', limit=50)
            self.assertEqual(len(models), len(result['items']))
            self.assertEqual({series}, {p['series'] for p in result['items']})

    def test_series_maker_specific_chipset_and_sort_compose(self):
        names = ['ASUS RTX 4070 SUPER', 'MSI RTX 4070 SUPER', 'ASUS RTX 4070 Ti SUPER', 'ASUS RTX 4060', 'ASUS RTX 5070']
        with patch_backend(s, '_market_fetch_html', return_value=html_rows('gpu', 0, len(names), names)):
            result = s.market_products_response('gpu', series='RTX 40', maker='asus', sort='price_desc', source='danawa')
            exact = s.market_products_response('gpu', series='RTX 40', maker='asus', model='RTX 4070 SUPER', source='danawa')
        self.assertEqual(3, len(result['items']))
        self.assertEqual(sorted([p['price'] for p in result['items']], reverse=True), [p['price'] for p in result['items']])
        self.assertEqual(['ASUS RTX 4070 SUPER'], [p['name'] for p in exact['items']])

    def test_fuzzy_series_provider_can_fall_back_to_known_chipset_queries(self):
        def fetch(url, provider, timeout=8):
            query = parse_qs(urlparse(url).query)['query'][0]
            name = 'ASUS RTX 4070' if '4070' in query else 'ASUS RTX 5070'
            return html_rows('gpu', 0, 40, [name + f' SKU {i}' for i in range(40)])
        with patch_backend(s, '_market_fetch_html', side_effect=fetch), patch.dict(s.CATALOGS, {'gpu':[{'name':'RTX 4070'}, {'name':'RTX 4080'}]}):
            result = s.market_products_response('gpu', series='RTX 40', maker='asus', limit=50, source='danawa')
        self.assertEqual(40, len(result['items']))
        self.assertTrue(all(p['series'] == 'RTX 40' for p in result['items']))

    def test_chipset_fallback_keeps_original_free_text_query(self):
        def fetch(url,provider,timeout=8):
            query = parse_qs(urlparse(url).query)['query'][0]
            if '4070' not in query:
                return html_rows('gpu',0,0)
            name = 'ASUS RTX 4070' if 'ASUS' in query else 'MSI RTX 4070'
            return html_rows('gpu',0,17,[name]*17)
        with patch_backend(s,'_market_fetch_html',side_effect=fetch), patch.dict(s.CATALOGS,{'gpu':[{'chipset':'RTX 4070'}]}):
            result = s.market_products_response('gpu','ASUS',series='RTX 40',source='danawa',limit=50)
        self.assertEqual(17,len(result['items']))
        self.assertTrue(all(row['manufacturer']=='asus' for row in result['items']))

    def test_query_specific_invalid_page_does_not_abandon_chipset_fallback(self):
        def fetch(url,provider,timeout=8):
            query = parse_qs(urlparse(url).query)['query'][0]
            return '<html>Unrecognized search page</html>' if query == 'RTX 40' else html_rows('gpu',0,17,['ASUS RTX 4070']*17)
        with patch_backend(s,'_market_fetch_html',side_effect=fetch), patch.dict(s.CATALOGS,{'gpu':[{'chipset':'RTX 4070'}]}):
            result = s.market_products_response('gpu',series='RTX 40',source='danawa',limit=50)
        self.assertEqual(17,len(result['items']))

    def test_live_translated_text_matches_are_not_removed_again(self):
        names = ['인텔 코어i5-14세대 14400F 정품']
        with patch_backend(s, '_market_fetch_html', return_value=html_rows('cpu', 0, 1, names)):
            result = s.market_products_response('cpu', 'Intel', source='danawa',limit=50)
        self.assertEqual(1,len(result['items']))

    def test_partial_names_find_suffix_variants_and_translated_brands_in_every_category(self):
        cases = [
            ('cpu', '14600', ['Intel Core i5-14600', '인텔 코어i5-14세대 14600K', 'Intel Core i5-14600KF'], 'Intel Core i5-14400F'),
            ('cpu', '인텔', ['Intel Core i5-14600', '인텔 코어i5-14세대 14600K', 'Intel Core i5-14600KF'], 'AMD Ryzen 7 9800X3D'),
            ('cpu', 'i5-14600', ['인텔 코어i5-14세대 14600KF'], '인텔 코어i5-14세대 14400F'),
            ('mb', '에이수스 b650', ['ASUS PRIME B650M-A', 'ASUS TUF B650-PLUS'], 'MSI B650M'),
            ('ram', '삼성 ddr5', ['Samsung DDR5-5600 16GB', '삼성전자 DDR5 32GB'], 'Samsung DDR4 16GB'),
            ('ram', '삼성전', ['삼성전자 DDR5 32GB'], 'G.SKILL DDR5 32GB'),
            ('ram', '６０００ DDR5', ['G.SKILL DDR5 6000 32GB'], 'G.SKILL DDR5 5600 32GB'),
            ('ram', 'DDR5-6000', ['G.SKILL DDR5 6000 32GB', 'TeamGroup DDR5-6000 16GB'], 'Samsung DDR5-5600 16GB'),
            ('gpu', '4070', ['ASUS GeForce RTX 4070', 'MSI 지포스 RTX 4070 SUPER', 'GIGABYTE RTX 4070 Ti SUPER'], 'ASUS GeForce RTX 4060'),
            ('gpu', '지포스 RTX4070', ['ASUS GeForce RTX 4070 SUPER'], 'ASUS GeForce RTX 4060'),
            ('storage', '삼성 990', ['Samsung 990 PRO 1TB SSD', '삼성전자 990 EVO 2TB SSD'], 'Samsung 980 PRO 1TB SSD'),
            ('hdd', '씨게이트 barra', ['Seagate Barracuda 2TB HDD', '씨게이트 Barracuda 4TB HDD'], 'Seagate IronWolf 4TB HDD'),
            ('psu', '마이크로닉스 850', ['Micronics Classic II 850W', '마이크로닉스 ASTRO 850W'], 'Micronics Classic II 750W'),
            ('case', 'h5', ['NZXT H5 Flow Black', 'NZXT H5 Flow White'], 'NZXT H7 Flow'),
            ('software', '윈도우 11', ['Microsoft Windows 11 Home', '마이크로소프트 Windows 11 Pro'], 'Microsoft Windows 10 Home'),
        ]
        for kind, query, expected, other in cases:
            with self.subTest(kind=kind, query=query):
                s.MARKET_BROWSE_CACHE.clear()
                s.MARKET_SEARCH_CACHE.clear()
                names = expected + [other]
                with patch_backend(s, '_market_fetch_html', return_value=html_rows(kind, 0, len(names), names)):
                    result = s.market_products_response(kind, query, source='danawa')
                self.assertEqual(expected, [item['name'] for item in result['items']])

    def test_saved_search_uses_the_same_partial_name_rules(self):
        names = ['Intel Core i5-14600', 'Intel Core i5-14600K', 'Intel Core i5-14600KF', 'AMD Ryzen 7 9800X3D']
        rows = [dict(id=str(i), name=name, price=200000, url=f'https://prod.danawa.com/info/?pcode={i+100}&cate=113973')
                for i, name in enumerate(names)]
        with patch_backend(s, 'saved_products', return_value=rows):
            for query in ['인텔', '14600']:
                with self.subTest(query=query):
                    result = s.saved_market_page('cpu', query, 1, 50, 'danawa')
                    self.assertEqual(names[:3], [item['name'] for item in result['items']])

    def test_partial_browse_search_does_not_weaken_exact_price_identity(self):
        self.assertFalse(s.compatible_price_name('Intel Core i5-14600', 'Intel Core i5-14600KF'))
        self.assertFalse(s.compatible_price_name('RTX 4070', 'RTX 4070 Ti SUPER'))
        self.assertFalse(s.compatible_price_name('Samsung 990 PRO 2TB', 'Samsung 990 PRO 1TB'))

    def test_partial_and_exact_source_queries_keep_independent_caches(self):
        names = ['Intel Core i5-14600', 'Intel Core i5-14600K', 'Intel Core i5-14600KF']
        with patch_backend(s, '_market_fetch_html', return_value=html_rows('cpu', 0, len(names), names)) as fetch:
            partial = s._market_source_page('cpu', '14600', 1, 40, 'danawa')
            exact = s._market_source_page('cpu', '14600', 1, 40, 'danawa', exact_query=True)
            cached_partial = s._market_source_page('cpu', '14600', 1, 40, 'danawa')
        self.assertEqual(names, [row['name'] for row in partial['items']])
        self.assertEqual(names[:1], [row['name'] for row in exact['items']])
        self.assertEqual(names, [row['name'] for row in cached_partial['items']])
        self.assertEqual(2, fetch.call_count)

    def test_compuzone_partial_cpu_query_keeps_suffix_variants(self):
        names = ['Intel Core i5-14600', '인텔 Core i5-14600K', 'Intel Core i5-14600KF', 'Intel Core i5-14400F']
        html = '<ul>' + ''.join(
            f'<li id="li-pno-{code}"><a class="prdTxt" href="../product/product_detail.htm?ProductNo={code}&MediumDivNo=1012">{name}</a><div class="prd_price" data-price="200000"></div></li>'
            for code, name in enumerate(names, 10000)
        ) + '</ul>'
        with patch_backend(s, '_market_fetch_html', return_value=html):
            result = s.market_products_response('cpu', '14600', source='compuzone')
        self.assertEqual(names[:3], [row['name'] for row in result['items']])

    def test_search_cache_remains_bounded_with_query_and_cursor_keys(self):
        with patch_backend(s, '_market_fetch_html', return_value=html_rows('cpu',0,0)):
            for i in range(150):
                s.market_products_response('cpu',f'query-{i}',source='danawa')
        self.assertLessEqual(len(s.MARKET_SEARCH_CACHE),128)

    def test_structured_chipset_wins_over_marketing_title(self):
        self.assertEqual('RTX 40', s.gpu_search_metadata({'chipset':'RTX 4070 SUPER', 'name':'RTX 5070 promotion'})['series'])

    def test_repeated_provider_rows_and_saved_overlap_do_not_duplicate(self):
        with patch_backend(s, '_market_fetch_html', return_value=html_rows('mb', 0, 40)):
            first = s.market_products_response('mb', source='danawa', limit=50)
            second = s.market_products_response('mb', source='danawa', limit=50, page=2)
        self.assertEqual(40, len(first['items']))
        self.assertEqual([], second['items'])
        self.assertFalse(second['has_more'])

if __name__ == '__main__': unittest.main()
