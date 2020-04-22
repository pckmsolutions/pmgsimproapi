from unittest import TestCase
from pmgsimproapi.util import to_tree
from pprint import pprint as pp

test_groups = [
        {'ID': 202, 'Name': 'Granite', 'ParentGroup': {}},
        {'ID': 47, 'Name': 'Kitchen Worktops 20mm', 'ParentGroup': {}},
        {'ID': 566, 'Name': 'Slabs', 'ParentGroup': {'ID': 202, 'Name': 'Granite'}},
        {'ID': 206, 'Name': 'Tiles', 'ParentGroup': {'ID': 202, 'Name': 'Granite'}},
        {'ID': 150,
            'Name': 'Granite',
            'ParentGroup': {'ID': 47, 'Name': 'Kitchen Worktops 20mm'}},
        {'ID': 148,
            'Name': 'Marble',
            'ParentGroup': {'ID': 47, 'Name': 'Kitchen Worktops 20mm'}},
        {'ID': 145,
            'Name': 'Terrazzo',
            'ParentGroup': {'ID': 47, 'Name': 'Kitchen Worktops 20mm'}},
        {'ID': 567, 'Name': '20mm', 'ParentGroup': {'ID': 566, 'Name': 'Slabs'}},
        {'ID': 568, 'Name': '30mm', 'ParentGroup': {'ID': 566, 'Name': 'Slabs'}},
        {'ID': 207, 'Name': '20mm', 'ParentGroup': {'ID': 206, 'Name': 'Tiles'}},
        {'ID': 208, 'Name': '30mm', 'ParentGroup': {'ID': 206, 'Name': 'Tiles'}},
        ]

expected = [
        {'ID': 47, 'Name': 'Kitchen Worktops 20mm', 'ParentGroup': {}, 'children': [
            {'ID': 150,
                'Name': 'Granite',
                'ParentGroup': {'ID': 47, 'Name': 'Kitchen Worktops 20mm'},
                'children': []},
            {'ID': 148,
                'Name': 'Marble',
                'ParentGroup': {'ID': 47, 'Name': 'Kitchen Worktops 20mm'},
                'children': []},
            {'ID': 145,
                'Name': 'Terrazzo',
                'ParentGroup': {'ID': 47, 'Name': 'Kitchen Worktops 20mm'},
                'children': []},
            ]},
        {'ID': 202, 'Name': 'Granite', 'ParentGroup': {}, 'children': [
            {'ID': 566, 'Name': 'Slabs', 'ParentGroup': {'ID': 202, 'Name': 'Granite'}, 'children': [
                {'ID': 567, 'Name': '20mm', 'ParentGroup': {'ID': 566, 'Name': 'Slabs'},
                    'children': []},
                {'ID': 568, 'Name': '30mm', 'ParentGroup': {'ID': 566, 'Name': 'Slabs'},
                    'children': []},
                ]},
            {'ID': 206, 'Name': 'Tiles', 'ParentGroup': {'ID': 202, 'Name': 'Granite'}, 'children': [
                {'ID': 207, 'Name': '20mm', 'ParentGroup': {'ID': 206, 'Name': 'Tiles'},
                    'children': []},
                {'ID': 208, 'Name': '30mm', 'ParentGroup': {'ID': 206, 'Name': 'Tiles'},
                    'children': []},
                ]},
            ]},
        ]

class UtilTestCase(TestCase):
    def test_to_tree(self):
        tree = sorted(to_tree(test_groups), key=lambda i: i['ID'])
        pp(tree)
        self.assertEqual(sorted(tree, key=lambda i: i['ID']), expected)

