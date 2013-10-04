from five import grok

from seantis.people.interfaces import IList
from seantis.people.browser import BaseView
from seantis.people.supermodel import get_table_columns_merged

class ListView(BaseView):

    permission = 'zope2.View'
    grok.require(permission)
    grok.context(IList)
    grok.name('view')

    template = grok.PageTemplateFile('templates/list.pt')

    def columns(self):
        used_type = self.context.used_type()

        if not used_type:
            return []

        return list(get_table_columns_merged(used_type.lookupSchema()))