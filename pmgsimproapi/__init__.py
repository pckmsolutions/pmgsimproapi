from pmgrestclient import ApiBase, json_headers_response_hander
from logging import getLogger
from datetime import datetime, timedelta
from os.path import basename
from base64 import b64encode
from pmgrestclient.paging import get_all_from_pages, Cache
from .util import to_tree
from collections import namedtuple

logger = getLogger(__name__)

class NotLoggedInError(Exception):
    pass

Page = namedtuple('Page', 'items page_number number_of_pages total_count')

class SimProApi(ApiBase):
    MAX_PAGE_SIZE = 250

    def __init__(self, base_url, client_id, client_secret, company=0, user=None, password=None):
        super(SimProApi, self).__init__(f'{base_url}/api/v1.0')
        self.base_url = base_url
        self.token_type = None
        self.access_token = None
        self.catelogue_item_custom_fields_cache = Cache(self._catelogue_item_custom_fields)
        self.suppliers_cache = Cache(self._get_suppliers)
        self.client_id = client_id
        self.client_secret = client_secret
        self.company = company
        self.company_prefix = f'companies/{company}'
        if user and password:
            self.login(user, password)

    def login(self, user, password):
        logger.info('Logging in')
        data = {
                'grant_type': 'password',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'username': user,
                'password': password,
                }
        self._handle_token_call(data)

    def get_job_pages(self, page_size, params=None, columns=None):
        page_number = 1
        while True:
            yield self._get_page(f'{self.company_prefix}/jobs/', page_number, page_size,
                params=params, columns=columns)
            page_number += 1

    def get_invoice_pages(self, page_size, params=None, columns=None):
        page_number = 1
        while True:
            page = self._get_page(f'{self.company_prefix}/customerInvoices/',
                    page_number, page_size, params=params, columns=columns)
            yield page
            page_number += 1
            if page_number >= page.number_of_pages:
                break

    def get_site(self, site_id):
        return self.get(f'{self.company_prefix}/sites/{site_id}')



    def _paging_get_all(self, path, **kwargs): 
        given_params = kwargs.get('params') or {} # different from straight default because None might have been passed
        def next_page(page_number):
            logger.debug(f'getting page {page_number} for {path}, args {kwargs}')
            ret = self.get(path, params={**given_params, **dict(page=page_number, pageSize=self.MAX_PAGE_SIZE)})
            return (ret, len(ret) >= self.MAX_PAGE_SIZE) if ret else ([], False)
        return get_all_from_pages(next_page)

    def get_storage_devices(self):
        return self._paging_get_all(f'{self.company_prefix}/storageDevices/')

    def create_storage_device(self, name, is_default=False):
        data = {'Name': name, 'IsDefault': is_default}
        return self.post(f'{self.company_prefix}/storageDevices/', data=data)

    def get_all_catelogue_groups(self, params=None):
        return self._get_all(self.get_catelogue_groups_page, params)

    def get_catelogue_groups_page(self, page, page_size, params=None, columns=None):
        return self._get_page(f'{self.company_prefix}/catalogGroups/', page, page_size, params=params, columns=columns)

    def create_catelougue_group(self, name, parent_id = None):
        data={'Name': name}
        if parent_id:
            data['ParentGroup'] = parent_id
        return self.post(f'{self.company_prefix}/catalogGroups/', data=data)

    def ensure_path(self, names, flat_existing, is_child, create, parent_id = 0):
        if not isinstance(names, list):
            names = [names]
        found = next((g for g in flat_existing if g.get('Name') == names[0] and is_child(g, parent_id)), None) if len(names) and names[0] else {'ID': 0}

        if found is not None:
            return found if len(names) <= 1 else self.ensure_path(names[1:], flat_existing, is_child, create, parent_id=found['ID'])

        for name in names:
            created = create(name, parent_id)
            parent_id = created['ID']
        return created

    def get_path(self, names, flat_existing, is_child, parent_id = 0):
        if not isinstance(names, list):
            names = [names]
        found = next((g for g in flat_existing if g.get('Name') == names[0] and is_child(g, parent_id)), None) if len(names) and names[0] else {'ID': 0}

        if found is not None:
            return found if len(names) <= 1 else self.get_path(names[1:], flat_existing, is_child, parent_id=found['ID'])

    # Catalogue Items custome fields
    def _catelogue_item_custom_fields(self):
        return self._paging_get_all(f'{self.company_prefix}/setup/customFields/catalogs/')

    @property
    def catelogue_item_custom_fields(self):
        return self.catelogue_item_custom_fields_cache.items

    def create_catelogue_item_custom_field(self, data):
        return self.post(f'{self.company_prefix}/setup/customFields/catalogs/', data=data)

    def ensure_catelogue_item_custom_field(self, name):
        fields = self.catelogue_item_custom_fields
        field = next((f for f in fields if f.get('Name') == name), None)
        if field is not None:
            return field;
        return self.create_catelogue_item_custom_field({'Name': name, 'Type': 'Text'})

    # Catalogue Items
    @staticmethod
    def _is_attachment_folder_child_of_parent(folder, parent_id):
        return folder.get('ParentID', 0) == parent_id

    def get_all_catelogue_items(self, params=None):
        return self._get_all(self.get_catelogue_items_page, params)

    def get_catelogue_items_page(self, page, page_size, params=None, columns=None):
        return self._get_page(f'{self.company_prefix}/catalogs/', page, page_size, params=params, columns=columns)

    def create_catelogue_item(self, data):
        return self.post(f'{self.company_prefix}/catalogs/', data=data)

    def get_catelogue_item(self, item_id):
        return self.get(f'{self.company_prefix}/catalogs/{item_id}')

    def delete_catelogue_item(self, item_id):
        return self.delete(f'{self.company_prefix}/catalogs/{item_id}')

    def update_catelogue_item(self, item_id, **kwargs):
        return self.patch(f'{self.company_prefix}/catalogs/{item_id}', data=kwargs)

    def get_catelogue_item_custom_fields(self, item_id):
        return self.get(f'{self.company_prefix}/catalogs/{item_id}/customFields/')

    def get_catelogue_item_attachments_files(self, item_id, params=None):
        return self._paging_get_all(f'{self.company_prefix}/catalogs/{item_id}/attachments/files/', params=params)

    def delete_catelogue_item_attachments_files(self, item_id, file_id):
        return self.delete(f'{self.company_prefix}/catalogs/{item_id}/attachments/files/{file_id}')

    def get_catelogue_item_attachments_folders(self, item_id, params=None):
        return self._paging_get_all(f'{self.company_prefix}/catalogs/{item_id}/attachments/folders/', params=params)

    def create_catelogue_item_attachments_folder(self, item_id, name, parent_id = 0):
        return self.post(f'{self.company_prefix}/catalogs/{item_id}/attachments/folders/', data={'Name': name, 'ParentID': parent_id})

    def update_custom_catelogue_field(self, cateloge_item_id, cust_field_id, value):
        return self.patch(f'{self.company_prefix}/catalogs/{cateloge_item_id}/customFields/{cust_field_id}', data={'Value': str(value)}) 

    def ensure_catelogue_item_attachment_folder(self, item_id, names, parent_id = 0):
        existing = self.get_catelogue_item_attachments_folders(item_id)
        def create(name, parent_id):
            return self.create_catelogue_item_attachments_folder(item_id, name, parent_id)
        return self.ensure_path(names, existing, self.__class__._is_attachment_folder_child_of_parent, create, parent_id)

    def attach_catelogue_file(self, cateloge_item_id, path, folder_id = None, default = False):
        with open(path, 'rb') as cat_file:
            data = {'Filename': basename(path),
                    'Base64Data': b64encode(cat_file.read()).decode(),
                    'Default': default}
            if folder_id:
                data['Folder'] = folder_id
            return self.post(f'{self.company_prefix}/catalogs/{cateloge_item_id}/attachments/files/', data=data)

    # Suppliers
    def _get_suppliers(self, **kwargs):
        return self._paging_get_all(f'{self.company_prefix}/0/vendors/')

    def create_supplier(self, name):
        new_supplier = self.post(f'{self.company_prefix}/0/vendors/', data={'Name': name})
        logger.debug(f'New supplier created {new_supplier}')
        self.suppliers_cache.append(new_supplier)

        return new_supplier

    def ensure_supplier(self, name):
        supplier = next((s for s in self.suppliers if s['Name'] == name), None)
        if supplier:
            return supplier
        logger.debug(f'Creating supplier {name}')
        return self.create_supplier(name)

    def add_supplier(self, catelogue_item_id, **kwargs):
        if not 'id' in kwargs:
            supp = self.ensure_supplier(kwargs['name'])
            return self.add_supplier(catelogue_item_id, **{**dict(id=supp['ID']), **kwargs})
        return self.post(f'{self.company_prefix}/catalogs/{catelogue_item_id}/vendors/', data={'Vendor': kwargs['id'], 'VendorPartNo': kwargs.get('ref','')})

    def get_suppliers(self, catelogue_item_id):
        return self.get(f'{self.company_prefix}/catalogs/{catelogue_item_id}/vendors/')

    def delete_supplier(self, catelogue_item_id, supplier_id):
        return self.delete(f'{self.company_prefix}/catalogs/{catelogue_item_id}/vendors/{supplier_id}')

    @property
    def suppliers(self):
        return self.suppliers_cache.items

    # Pricing
    def get_pricing_tier(self, id):
        return self.get(f'{self.company_prefix}/setup/materials/pricingTiers/{id}')

    def get_all_pricing_tiers(self, params=None, columns=None):
        return self._get_all(self.get_pricing_tiers_page, params, columns)

    def get_pricing_tiers_page(self, page, page_size, params=None, columns=None):
        return self._get_page(f'{self.company_prefix}/setup/materials/pricingTiers/', page, page_size, params=params, columns=columns)

    def headers(self, **kwargs):
        if datetime.now() + timedelta(seconds=4) >= self.expires:
            logger.info('Refreshing token')
            data = {
                    'grant_type': 'refresh_token',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'refresh_token': self.refresh_token,
                    }
            self._handle_token_call(data)

        if not self.token_type or not self.access_token:
            raise NotLoggedInError()
        return {'Authorization': f'{self.token_type} {self.access_token}',
                'Content-Type': 'application/json'}

    def _get_all(self, page_getter, params=None, columns=None):
        def next_page(page_number):
            ret = page_getter(page=page_number, page_size=self.MAX_PAGE_SIZE, params=params, columns=columns)
            return ret['items'], ret['page'] < ret['pages']

        return get_all_from_pages(next_page)

    def _get_page(self, path, page, page_size, params=None, columns=None):
        params={**dict(page=page, pageSize=page_size), **(params or {})}
        if columns:
            params['columns'] = ','.join(columns)

        items, headers = self.get(path,
                params=params,
                response_handler=json_headers_response_hander
                )

        return Page(items=items, page_number=page, number_of_pages=int(headers['Result-Pages']),
                total_count=int(headers['Result-Total']))


#        return dict(items=items, total_count=int(headers['Result-Total']), pages=int(headers['Result-Pages']),
#                page_size=int(headers.get('Result-Count', 0)), page=page)

    def _handle_token_call(self, data):
        logger_in = ApiBase(self.base_url)
        resp = logger_in.post('oauth2/token', data=data)
        self.access_token = resp['access_token']
        self.refresh_token = resp['refresh_token']
        self.token_type = resp['token_type']
        self.expires = datetime.now() + timedelta(seconds=resp['expires_in'])
        logger.info(f'simPRO token expires {self.expires.isoformat()}')


class SimProCatelogue(object):
    def __init__(self, api, columns = [], updating=True):
        self.api = api
        self.updating = updating
        self.catelogue_items_cache = Cache(self._get_catelogue_items)
        self.columns = ','.join(columns)
        self.group_caches = {}

    @property
    def items(self):
        return self.catelogue_items_cache.items

    def create_catelogue_item(self, **kwargs):
        logger.debug(f'Creating item {kwargs}')
        new_item = self.api.create_catelogue_item(kwargs)
        if self.updating:
            self.catelogue_items_cache.append(new_item)
        return new_item

    def get_by_part_no(self, group_id, part_no):
        return next(iter(self.api.get_catelogue_items(params=self._params({'PartNo': part_no, 'Group.ID': group_id}))), None)

    def get_group(self, group_id):
        def ret():
            return self.api.get_catelogue_items(params=self._params({'Group.ID': group_id}))
        if self.updating:
            return ret()
        if not group_id in self.group_caches:
            self.group_caches[group_id] = Cache(ret)
        return self.group_caches[group_id].items

    def _get_catelogue_items(self):
        return self.api.get_catelogue_items(params=self._params());

    def _params(self, params={}):
        return {**params, **{'columns': self.columns}} if self.columns else params

#class SimProCatelogueGroupTree(object):
#    def __init__(self, api, rootgoups):
#        self.rootgoups = rootgoups
#
#    def tree(self):
#        def children(parent_id):
#            return simpro.get_all_catelogue_groups(params={'ParentGroup.ID': parent_id})
#
#        return list(map(lambda g: {**g: **dict(children=children(g['ID']))}, rootgoups)
#
#def group_tree(groups):
#    def add_children(group):
#        children = api.get_all_catelogue_groups(params={'ParentGroup.ID': group['ID']})
#        if children:
#            group['children'] = children

#def to_tree(groups):
#    def get_children(parent_id)
#         children = api.get_all_catelogue_groups(params={'ParentGroup.ID': parent_id})
#         return map(lambda i: {**i, **dict(children=list(get_children(i['ID'])))}, groups)






class SimProCatelogueGroup(object):
    def __init__(self, api):
        self.api = api
        self.catelogue_groups_cache = Cache(self.api.get_all_catelogue_groups)

    def create_catelougue_group(self, name, parent_id = None):
        new_group = self.api.create_catelougue_group(name, parent_id)
        self.catelogue_groups_cache.append(new_group)
        return new_group

    def get_catelogue_group(self, names, parent_id = 0):
        return self.api.get_path(names, self.catelogue_groups, self.__class__._is_group_child_of_parent, parent_id)

    def ensure_catelogue_group(self, names, parent_id = 0):
        return self.api.ensure_path(names, self.catelogue_groups, self.__class__._is_group_child_of_parent, self.create_catelougue_group, parent_id)

    def tree(self):
        return to_tree(self.catelogue_groups)

    @property
    def catelogue_groups(self):
        return self.catelogue_groups_cache.items

    @staticmethod
    def _is_group_child_of_parent(group, parent_id):
        return group.get('ParentGroup', {}).get('ID', 0) == parent_id

    @staticmethod
    def to_tree(api, items):
        def children(parent_id):
           c = api.get_all_catelogue_groups(params={'ParentGroup.ID': parent_id})
           return map(lambda i: {**i, **dict(children=list(children(i['ID'])))}, c)
        return list(map(lambda i: {**i, **dict(children=list(children(i['ID'])))}, items))


class SimProStorageDevice(object):
    def __init__(self, api):
        self.cache = Cache(self._load)

    def _load(self):
        return self.api.get_storage_devices()

    def create(self, name, is_default=False):
        new_one = self.api.create(name, is_default)
        self.cache.append(new_one)
        return new_one

    def ensure(self, name, is_default=False):
        found = next((item for item in items if item['Name'] == name), None)
        if found:
            return found
        return self.create(name, is_default)

    @property
    def items(self):
        return self.cache.items


