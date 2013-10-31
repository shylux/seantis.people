from lxml import etree

from plone.supermodel.parser import ISchemaMetadataHandler

from plone.supermodel.utils import ns
from zope.interface import implements

from seantis.plonetools import tools

NAME_FROM_PERSON = u'seantis.people.name_from_person'
PERSON_COLUMNS = u'seantis.people.person_column'
PERSON_ORDER = u'seantis.people.order'
PERSON_SELECTABLE = u'seantis.people.selectable'
PERSON_DETAILS = u'seantis.people.details'

# Supermodel namespace and prefix
PEOPLE_NAMESPACE = 'http://namespaces.plone.org/supermodel/people'
PEOPLE_PREFIX = 'people'

missing = object()


def get_title_fields(schema):
    return schema.queryTaggedValue(NAME_FROM_PERSON, [])


def set_title_fields(schema, fields):
    schema.setTaggedValue(NAME_FROM_PERSON, sorted(
        list(set(fields)), key=fields.index  # unique values, preserving order
    ))


def get_selectable_fields(schema):
    return schema.queryTaggedValue(PERSON_SELECTABLE, [])


def set_selectable_fields(schema, fields):
    schema.setTaggedValue(PERSON_SELECTABLE, list(set(fields)))


def get_columns(schema):
    return schema.queryTaggedValue(PERSON_COLUMNS, [])


def set_columns(schema, columns):
    for column in columns:
        assert not isinstance(column, basestring), """
            A list of list is expected, not a list of strings.
        """
    schema.setTaggedValue(PERSON_COLUMNS, columns)

    for column in get_columns(schema):
        for field in column:
            tools.add_attribute_to_metadata(field)


def get_order(schema):
    return schema.queryTaggedValue(PERSON_ORDER, [])


def set_order(schema, order):
    schema.setTaggedValue(PERSON_ORDER, order)


def get_detail_fields(schema):
    return schema.queryTaggedValue(PERSON_DETAILS, {})


def set_detail_fields(schema, fields):
    schema.setTaggedValue(PERSON_DETAILS, fields)


class NodeHandler(object):

    namespace = PEOPLE_NAMESPACE
    prefix = PEOPLE_PREFIX

    def __init__(self, tagname):
        self.tagname = tagname
        etree.register_namespace(self.prefix, self.namespace)

    def prefixed(self, name):
        return ns(name, self.namespace)

    def nodes(self, node, name):
        return node.findall('./{}'.format(self.prefixed(name)))

    def tags(self, node):
        return self.nodes(node, self.tagname)


class ItemListHandler(NodeHandler):

    def __init__(self, tagname, getter, setter):
        super(ItemListHandler, self).__init__(tagname)
        self.getter = getter
        self.setter = setter

    def parse(self, schema_node, schema):
        tags = self.tags(schema_node)

        if not tags:
            return

        values = []

        for tag in tags:
            for item in self.nodes(tag, 'item'):
                values.append(item.text.strip())

        self.setter(schema, values)

    def write(self, schema_node, schema):
        values = self.getter(schema)

        if not values:
            return

        element = etree.Element(self.prefixed(self.tagname))
        for value in values:
            item = etree.Element(self.prefixed('item'))
            item.text = value

            element.append(item)

        schema_node.append(element)


class DetailsHandler(NodeHandler):

    def parse(self, schema_node, schema):
        tags = self.tags(schema_node)

        if not tags:
            return

        detail_fields = {}

        for tag in tags:
            position = tag.get('position') or 'left'
            detail_fields[position] = []

            for item in self.nodes(tag, 'item'):
                detail_fields[position].append(item.text.strip())

        set_detail_fields(schema, detail_fields)

    def write(self, schema_node, schema):
        detail_fields = get_detail_fields(schema)

        if not detail_fields:
            return

        for position, fields in detail_fields.items():
            element = etree.Element(self.prefixed(self.tagname))
            element.set('position', position)

            for field in fields:
                item = etree.Element(self.prefixed('item'))
                item.text = field

                element.append(item)

            schema_node.append(element)


class ColumnsHandler(NodeHandler):

    def parse(self, schema_node, schema):
        tags = self.tags(schema_node)

        if not tags:
            return

        columns = []
        selectable_fields = []

        for tag in tags:
            for column in self.nodes(tag, 'column'):
                items = self.nodes(column, 'item')

                if len(items) == 1 and column.get('selectable'):
                    selectable = True
                else:
                    selectable = False

                column = []
                for item in items:
                    value = item.text.strip()
                    column.append(value)

                    if selectable:
                        selectable_fields.append(value)

                columns.append(column)

        set_columns(schema, columns)
        set_selectable_fields(schema, selectable_fields)

    def write(self, schema_node, schema):
        columns = get_columns(schema)
        selectable_fields = get_selectable_fields(schema)

        if not columns:
            return

        columns_el = etree.Element(self.prefixed(self.tagname))

        for column in columns:
            column_el = etree.Element(self.prefixed('column'))

            if len(column) == 1 and column[0] in selectable_fields:
                column_el.set('selectable', 'true')

            for field in column:
                item_el = etree.Element(self.prefixed('item'))
                item_el.text = field
                column_el.append(item_el)

            columns_el.append(column_el)

        schema_node.append(columns_el)


class PeopleSchemaMetaHandler(object):

    implements(ISchemaMetadataHandler)

    namespace = PEOPLE_NAMESPACE
    prefix = PEOPLE_PREFIX

    handlers = [
        ItemListHandler('title', get_title_fields, set_title_fields),
        ItemListHandler('order', get_order, set_order),
        DetailsHandler('details'),
        ColumnsHandler('columns')
    ]

    def read(self, schema_node, schema):
        for handler in self.handlers:
            handler.parse(schema_node, schema)

    def write(self, schema_node, schema):
        for handler in self.handlers:
            handler.write(schema_node, schema)
