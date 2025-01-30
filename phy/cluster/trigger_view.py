from phylib.utils import emit
from phy.gui.widgets import Table, HTMLWidget

# -----------------------------------------------------------------------------
# Trigger view
# -----------------------------------------------------------------------------


class TriggerView(Table):
    """Display a table of triggers with their names and counts."""
    _view_name = 'trigger_view'

    def __init__(self, *args, data=None, columns=(), sort=None):
        HTMLWidget.__init__(
            self, *args, title=self.__class__.__name__, debounce_events=('select',))
        self._reset_table(data=data, columns=columns, sort=sort)

    def _reset_table(self, data=None, columns=(), sort=None):
        emit(self._view_name + '_init', self)
        if 'id' in columns:
            columns.remove('id')
        columns = ['id', 'name', 'n_triggers']
        sort = sort or ('name', 'asc')

        # Convert name to print-friendly strings
        for item in data:
            if isinstance(item['name'], bytes):
                item['name'] = item['name'].decode()

        self._init_table(columns=columns, data=data, sort=sort)
