from backend_patch import patch_backend
import unittest
from unittest.mock import patch
from product_filters import normalize_specs, matches_specs, facets
import server_fixed as s

class ProductFilterTests(unittest.TestCase):
    def test_representative_combinations_and_unknowns(self):
        examples=[
          ('cpu','Intel Core i5-14600KF','소켓1700 / DDR5, DDR4 / 14코어 / 20스레드', {'platform':['Intel'],'socket':['LGA1700'],'cpu_family':['Core i5']}),
          ('mb','ASUS TUF GAMING B650-PLUS','AMD AM5 / B650 / DDR5 / ATX / PCIe 4.0 x16', {'platform':['AMD'],'socket':['AM5'],'chipset':['B650'],'memory_type':['DDR5'],'form_factor':['ATX']}),
          ('ram','G.SKILL DDR5-6000 CL30 32GB (16GB×2)','PC용 / 1.35V / RGB / 화이트', {'memory_type':['DDR5'],'capacity_gb':['32'],'speed':['6000'],'cl':['30']}),
          ('storage','Samsung SSD 2TB M.2 2280','PCIe 4.0 x4 / NVMe 1.4 / TLC / 3D NAND / 읽기: 7,000MB/s / 쓰기: 6,500MB/s', {'form_factor':['M.2 2280'],'interface':['PCIe 4.0 x4'],'protocol':['NVMe'],'capacity_gb':['2000'],'nand':['TLC']}),
          ('psu','Seasonic 850W ATX 3.1','ATX 파워 / 80 PLUS Gold / Full Modular / 12V-2x6', {'form_factor':['ATX'],'watt_range':['800–899W'],'rating':['Gold'],'modular':['Full']}),
          ('hdd','Seagate NAS HDD 8TB','NAS용(3.5인치) / SATA3 / 7,200 RPM / 캐시: 256MB', {'usage':['NAS'],'capacity_gb':['8000'],'rpm':['7200']}),
        ]
        for kind,name,spec,filters in examples:
            with self.subTest(kind=kind):
                data=normalize_specs({'name':name,'spec_text':spec},kind)
                self.assertTrue(matches_specs(data,filters),data)
                self.assertFalse(matches_specs({},filters))
        ram=normalize_specs({'name':examples[2][1],'spec_text':examples[2][2]},'ram')
        self.assertEqual('16GB × 2',ram['kit'])
        self.assertFalse(matches_specs(ram,{'capacity_gb':['16']}))

    def test_no_guessed_specs_or_unrelated_pcie(self):
        board=normalize_specs({'name':'ASUS B650M','spec_text':'M-ATX / M.2 PCIe 5.0 / DDR5'},'mb')
        self.assertEqual('M-ATX',board['form_factor'])
        self.assertNotIn('pcie_x16',board)
        self.assertNotIn('socket',board)
        self.assertNotIn('led',normalize_specs({'name':'Samsung DDR5 16GB'},'ram'))
        self.assertNotIn('rating',normalize_specs({'name':'PSU Cybenetics Gold 850W'},'psu'))
        self.assertNotIn('capacity_gb',normalize_specs({'name':'SSD M.2','spec_text':'500GB / 1TB / 2TB'},'storage'))

    def test_dependent_chipsets_keep_selected_zero_result_option(self):
        rows=[{'name':'ASUS B650 PLUS','socket':'AM5'},{'name':'MSI B760','socket':'LGA1700'}]
        groups=facets('mb',rows,{'socket':['AM5']})
        chip=next(g for g in groups if g['key']=='chipset')
        self.assertEqual([['B650','B650']],chip['options'])
        groups=facets('mb',rows,{'socket':['AM5'],'chipset':['B760']})
        chip=next(g for g in groups if g['key']=='chipset')
        self.assertEqual(0,chip['counts']['B760'])

    def test_filters_before_pagination_preserve_prices_links_images(self):
        s.MARKET_SEARCH_CACHE.clear()
        rows=[{'id':str(i),'name':'ASUS B650 PLUS','socket':'AM5' if i%2 else 'AM4','spec_text':'DDR5 / ATX', 'url':f'https://prod.danawa.com/info/?pcode={10000+i}', 'image_url':f'https://example.com/{i}.png','price':200000-i,'price_status':'cached'} for i in range(240)]
        empty={'items':[],'has_more':False,'status':'empty','source_url':'','cached':False}
        with patch_backend(s,'saved_products',return_value=rows),patch_backend(s,'_market_source_page',return_value=empty):
            filters={'socket':['AM5'],'memory_type':['DDR5'],'form_factor':['ATX']}
            a=s.market_products_response('mb',filters=filters,sort='price_asc',source='danawa')
            b=s.market_products_response('mb',filters=filters,sort='price_asc',source='danawa',page=2,cursor=a['cursor'])
        self.assertEqual((50,50),(len(a['items']),len(b['items'])))
        self.assertFalse({r['id'] for r in a['items']} & {r['id'] for r in b['items']})
        allrows=a['items']+b['items']; prices=[r['price'] for r in allrows]
        self.assertEqual(sorted(prices),prices)
        self.assertTrue(all(r['specs']['socket']=='AM5' and r['image_url'] and r['url'] for r in allrows))

    def test_compact_catalog_does_not_send_retail_inventory(self):
        with patch_backend(s,'saved_products',return_value=[{'id':'retail-test','name':'ASUS B650','socket':'AM5'}]):
            data=s.catalog_response(compact=True)
        self.assertNotIn('retail-test',{r['id'] for r in data['mbs']})
        self.assertTrue(data['filter_facets']['mb'])

if __name__=='__main__': unittest.main()
