from collections import namedtuple
from datetime import  timezone
from logging import getLogger
from functools import wraps
from pmgaiorest import ApiBase
from typing import Optional, Dict
from logging import getLogger

logger = getLogger(__name__)

Page = namedtuple('Page', 'items page_number number_of_pages total_count')

DEFAULT_PAGE_SIZE = 50

logger = getLogger(__name__)

def params_add_columns(*columns, params:Optional[Dict]=None):
    if not params:
        params = {}
    params['columns'] = ','.join(columns)
    return params

class SimProApi(ApiBase):
    def __init__(self, aiohttp_session, base_url, header_args,
            handle_reconnect=None):
        super().__init__(aiohttp_session,
                base_url,
                header_args=header_args,
                handle_reconnect=handle_reconnect)

    # Setup
    async def get_setup_project_custom_fields(self,*,
            name: Optional[str] = None,
            show_for_leads: Optional[bool] = None,
            show_for_quotes: Optional[bool] = None,
            show_for_jobs: Optional[bool] = None,
            show_for_recurring: Optional[bool] = None,
            ):
        params={}

        if name is not None:
            params['Name'] = name

        def add_show_for(subtype, show):
            if show is not None:
                params[f'ShowFor.{subtype}'] = 'true' if show else 'false'

        add_show_for('Leads', show_for_leads)
        add_show_for('Quotes', show_for_quotes)
        add_show_for('Jobs', show_for_jobs)
        add_show_for('Recurring', show_for_recurring)

        return await self.get(f'setup/customFields/projects/',
                params=params)

    async def create_setup_project_custom_fields(self, *,
            name: str,
            type: Optional[str] = "Text",
            show_for_leads: Optional[bool] = False,
            show_for_quotes: Optional[bool] = False,
            show_for_jobs: Optional[bool] = False,
            show_for_recurring: Optional[bool] = False,
            is_mandatory: Optional[bool] = False,
            ):
        return await self.post(f'setup/customFields/projects/', json={
            "Name": name,
            "Type": type,
            "IsMandatory": is_mandatory,
            "ShowFor": {
                "Leads": show_for_leads,
                "Quotes": show_for_quotes,
                "Jobs": show_for_jobs,
                "Recurring": show_for_recurring
                }
            })

    # Invoices
    async def get_invoice_pages(self, *,
            page_size=None, params=None, modified_since=None):
        async for page in self._get_pages(
                self.get_invoice_page,
                page_size=page_size,
                params=params,
                modified_since=modified_since):
            yield page

    async def get_invoice_page(self, *,
            page_number=1, page_size=None, params=None, modified_since=None):
        return await self._get_page('customerInvoices/',
                    page_number, page_size, params, modified_since)

    #  sites
    async def get_site(self, site_id):
        return await self.get(f'sites/{site_id}')

    # Prebuilds
    async def get_prebuild_group_pages(self, *,
            page_size=None, params=None, modified_since=None):
        async for page in self._get_pages(
                self.get_prebuild_group_page,
                page_size=page_size,
                params=params,
                modified_since=modified_since):
            yield page

    async def get_prebuild_group_page(self, *,
            page_number=1, page_size=None, params=None, modified_since=None):
        return await self._get_page('prebuildGroups/',
                    page_number, page_size, params, modified_since)

    async def get_prebuild_group(self, *, name: Optional[str] = None,
            parent_id: Optional[int] = None):
        assert name is not None

        params={'Name': name}
        if parent_id is not None:
            params['ParentGroup.ID'] = parent_id
        prebuild_page = await self.get_prebuild_group_page(params=params)
        if prebuild_page.total_count > 1:
            logger.error('Got multiple prebuild groups')
            return None

        if prebuild_page.total_count < 1:
            logger.error('Prebuild group not found')
            return None

        return prebuild_page.items[0]

    async def create_prebuild_group(self, *, name, parent_id):
        return await self.post('prebuildGroups/', json={
            'Name': name,
            'ParentGroup': parent_id,
            })

    async def get_prebuild_std_price_pages(self, *,
            page_size=None, params=None, modified_since=None,
            group_id: Optional[int] = None):
        if params is None:
            params = {}
        if group_id is not None:
            params['Group.ID'] = group_id
        async for page in self._get_pages(
                self.get_prebuild_std_price_page,
                page_size=page_size,
                params=params,
                modified_since=modified_since):
            yield page

    async def get_prebuild_std_price_page(self, *,
            page_number=1, page_size=None, params=None, modified_since=None):
        return await self._get_page('prebuilds/standardPrice/',
                    page_number, page_size, params, modified_since)

    async def get_prebuild_std_price(self, *,
            prebuild_id: Optional[int] = None,
            part_no: Optional[str] = None,
            group_id: Optional[int] = None,
            params: Optional[Dict] = None):

        if prebuild_id is not None:
            return await self.get(f'prebuilds/standardPrice/{prebuild_id}', params=params)

        assert part_no is not None

        if params is None:
            params = {} 
 
        params['PartNo'] = part_no
        if group_id is not None:
            params['Group.ID'] = group_id

        return await self.get('prebuilds/standardPrice/', params=params)

    async def create_prebuild_std_price(self, *,
            group_id, part_no, name, description):
        return await self.post('prebuilds/standardPrice/', json={
            'Group': group_id,
            'PartNo': part_no,
            'Name': name,
            'Description': description,
            })

    async def update_prebuild_std_price(self, prebuild_id:int, *,
            group_id: Optional[int] = None,
            part_no: Optional[str] = None,
            name: Optional[str] = None,
            description: Optional[str] = None,
            total_ex: Optional[float] = None):
        json = {}
        def add_setter(name, val):
            if val is not None:
                json[name] = val
        add_setter('Group', group_id)
        add_setter('PartNo', part_no)
        add_setter('Name', name)
        add_setter('Description', description)
        add_setter('TotalEx', total_ex)

        return await self.patch(f'prebuilds/standardPrice/{prebuild_id}', json=json)

    async def get_prebuild_catalogs(self, prebuild_id:int):
        return await self.get(f'prebuilds/{prebuild_id}/catalogs/')

    async def create_prebuild_catalog(self, prebuild_id:int, *,
            catalog_id, quantity):
        return await self.post(f'prebuilds/{prebuild_id}/catalogs/', json={
            'Catalog': catalog_id,
            'Quantity': quantity,
            })

    async def del_prebuild_catalog(self, prebuild_id:int, catalog_id:int):
        return await self.delete(f'prebuilds/{prebuild_id}/catalogs/{catalog_id}')

    async def get_prebuild_attachments(self, prebuild_id:int):
        return await self.get(f'prebuilds/{prebuild_id}/attachments/files/')

    async def del_prebuild_attachment(self, prebuild_id:int, attachment_id:int):
        return await self.delete(f'prebuilds/{prebuild_id}/attachments/files/{attachment_id}')

    async def add_prebuild_attachment(self, prebuild_id:int, *, name, content, default):
        return await self.post(f'prebuilds/{prebuild_id}/attachments/files/', json={
            'Filename': name,
            'Base64Data': content,
            'Default': default
            })
     

    # Catalog
    async def get_catalog_pages(self, *,
            page_size=None, params=None, modified_since=None):
        async for page in self._get_pages(
                self.get_catalog_page,
                page_size=page_size,
                params=params,
                modified_since=modified_since):
            yield page

    async def get_catalog_page(self, *,
            page_number=1, page_size=None, params=None, modified_since=None):
        return await self._get_page('catalogs/',
                    page_number, page_size, params, modified_since)

    async def get_catalog(self, *, part_no:str, params=None):
        params = params or {}
        params['PartNo'] = part_no

        catalogs = await self.get(f'catalogs/', params=params)
        if len(catalogs) > 1:
            logger.error('Got multiple catalogs for part no %s', part_no)
            return None

        if len(catalogs) < 1:
            logger.error('Catalog part no %s not found', part_no)
            return None

        return catalogs[0]

    async def update_catalog(self, *, catalog_id: int,
            estimated_time: Optional[int] = None):
        json = {}
        def add_setter(name, val):
            if val is not None:
                json[name] = val
        add_setter('EstimatedTime', estimated_time)
        if not json:
            logger.error('Required at least 1 field to update catalog' +
            '(catalog_id: %d)', catalog_id)
            return None

        return await self.patch(f'catalogs/{catalog_id}', json=json)

    # Quotes
    async def get_quote_pages(self, *,
            page_size=None, params=None, modified_since=None):
        async for page in self._get_pages(
                self.get_quote_page,
                page_size=page_size,
                params=params,
                modified_since=modified_since):
            yield page

    async def get_quote_page(self, *,
            page_number=1, page_size=None, params=None, modified_since=None):
        return await self._get_page('quotes/',
                    page_number, page_size, params, modified_since)

    async def get_quote_timeline(self, quote_id: int, *, part_no:str):
        return await self.get('quotes/{quote_id}/timelines/')


    # Leads
    async def get_lead_pages(self, *,
            page_size=None, params=None, modified_since=None):
        async for page in self._get_pages(
                self.get_lead_page,
                page_size=page_size,
                params=params,
                modified_since=modified_since):
            yield page

    async def get_lead_page(self, *,
            page_number=1, page_size=None, params=None, modified_since=None):
        return await self._get_page('leads/',
                    page_number, page_size, params, modified_since)

    async def get_lead(self, lead_id: int):
        return await self.get(f'leads/{lead_id}')

    async def get_lead_custom_fields(self, lead_id):
        return await self.get(f'leads/{lead_id}/customFields/')

    async def get_lead_custom_field(self, lead_id, custom_field_id):
        return await self.get(f'leads/{lead_id}/customFields/{custom_field_id}')

    async def update_lead_custom_field(self,
            lead_id: int,
            custom_field_id: int,
            value: str):
        return await self.patch(
                f'leads/{lead_id}/customFields/{custom_field_id}',
                json={
                    "Value": value
                    }
                )

    # Untilities
    async def _get_pages(self, page_callable, *,
            page_size=None, params=None, modified_since=None):
        page_number = 1
        while True:
            page = await page_callable(
                    page_number=page_number,
                    page_size=page_size,
                    params=params,
                    modified_since=modified_since)
            yield page
            page_number += 1
            if page_number >= page.number_of_pages:
                break

    async def _get_page(self, path, page_number, page_size, params, modified_since):
        params = params or {}
        params['page'] = page_number or 1
        params['pageSize'] = page_size or DEFAULT_PAGE_SIZE

        in_headers = {}
        if modified_since is not None:
            mod_time = modified_since.astimezone(tz=timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
            in_headers = {'If-Modified-Since': mod_time}

        json, headers = await self.get_with_headers(path, params=params, headers=in_headers)

        return Page(items=json, page_number=page_number, number_of_pages=int(headers['Result-Pages']),
                total_count=int(headers['Result-Total']))


