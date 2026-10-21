# Add-on Store Sort Memory - NVDA add-on
# Copyright (C) 2026 Jiří Holzinger <jiri.holzinger@gmail.com>
# This file is covered by the GNU General Public License, version 2 or later.
# See the file COPYING.txt for more details.

"""Remembers (or enforces) the sorting of the add-on list in the NVDA Add-on Store.

NVDA resets the "Sort by column" choice whenever the Add-on Store is opened
or the tab is changed. This plugin wraps the store dialog's tab-change
handler and applies the sort the user wants: either the last sort he chose
on that tab, or a fixed date sort configured in NVDA settings.
"""

import functools

import addonHandler
import config
import globalPluginHandler
import globalVars
import gui
import wx
from gui import guiHelper, settingsDialogs
from logHandler import log

addonHandler.initTranslation()

CONF_SECTION = "addonStoreSortMemory"

# Values of the per-tab "default sort" option.
SORT_NVDA = "nvda"
SORT_PUB_NEWEST = "pubNewest"
SORT_PUB_OLDEST = "pubOldest"
SORT_INSTALL_NEWEST = "installNewest"
SORT_INSTALL_OLDEST = "installOldest"
_SORT_VALUES = (SORT_NVDA, SORT_PUB_NEWEST, SORT_PUB_OLDEST, SORT_INSTALL_NEWEST, SORT_INSTALL_OLDEST)
_INSTALL_SORTS = (SORT_INSTALL_NEWEST, SORT_INSTALL_OLDEST)

MODE_REMEMBER = "remember"
MODE_FIXED = "fixed"

# Add-on Store tabs (names of addonStore.models.status._StatusFilterKey members)
# and the default sort used for each one.
TABS = ("INSTALLED", "UPDATE", "AVAILABLE", "INCOMPATIBLE")
# Tabs that have an "Install date" column.
TABS_WITH_INSTALL_DATE = ("INSTALLED", "INCOMPATIBLE")
_DEFAULT_TAB_SORT = {
	"INSTALLED": SORT_INSTALL_NEWEST,
	"UPDATE": SORT_PUB_NEWEST,
	"AVAILABLE": SORT_PUB_NEWEST,
	"INCOMPATIBLE": SORT_INSTALL_NEWEST,
}
# Key used in the remembered string when one sort is shared by all tabs.
SHARED_KEY = "ALL"

_optionList = ", ".join('"%s"' % v for v in _SORT_VALUES)
confspec = {
	"enabled": "boolean(default=True)",
	"mode": 'option("remember", "fixed", default="remember")',
	"rememberPerTab": "boolean(default=True)",
	"remembered": 'string(default="")',
	# Tab selected when the Add-on Store opens: "nvda", "last" or a tab name.
	"openTab": 'option("nvda", "last", "INSTALLED", "UPDATE", "AVAILABLE", "INCOMPATIBLE", default="nvda")',
	# Also use openTab when NVDA opens the store on Updatable add-ons (update notification).
	"openTabOverridesUpdates": "boolean(default=False)",
	"lastTab": 'string(default="")',
}
OPEN_NVDA = "nvda"
OPEN_LAST = "last"
for _tab in TABS:
	confspec["sort" + _tab] = 'option(%s, default="%s")' % (_optionList, _DEFAULT_TAB_SORT[_tab])
config.conf.spec[CONF_SECTION] = confspec


def _conf():
	return config.conf[CONF_SECTION]


def _listField(name):
	"""Return the AddonListField member called name, or None in NVDA versions without it."""
	try:
		from gui.addonStoreGui.viewModels.addonList import AddonListField
	except ImportError:
		return None
	return getattr(AddonListField, name, None)


def _choiceFields(listVM):
	"""Fields in the order used by the "Sort by column" combo box.

	NVDA 2026.2 and later put "Relevance" first (sortableFields);
	NVDA 2025.x uses only the visible columns (presentedFields).
	"""
	fields = getattr(listVM, "sortableFields", None)
	if fields is None:
		fields = listVM.presentedFields
	return list(fields)


def _fixedSortFor(tabName, fields):
	"""Translate the configured default sort of a tab to (field, reverse), or None for NVDA default."""
	value = _conf()["sort" + tabName]
	if value == SORT_NVDA:
		return None
	pub = _listField("publicationDate")
	inst = _listField("installDate")
	if value in _INSTALL_SORTS:
		field = inst if inst in fields else pub
	else:
		field = pub
	if field is None or field not in fields:
		return None
	# Dates sort ascending (oldest first); reverse gives newest first.
	reverse = value in (SORT_PUB_NEWEST, SORT_INSTALL_NEWEST)
	return field, reverse


def _parseRemembered():
	result = {}
	for item in _conf()["remembered"].split("|"):
		key, sep, value = item.partition("=")
		fieldName, sep2, rev = value.partition(":")
		if sep and sep2 and key and fieldName:
			result[key] = (fieldName, rev == "1")
	return result


def _storeRemembered(data):
	_conf()["remembered"] = "|".join(
		"%s=%s:%d" % (key, fieldName, 1 if rev else 0) for key, (fieldName, rev) in sorted(data.items())
	)


def _rememberKey(tabName):
	return tabName if _conf()["rememberPerTab"] else SHARED_KEY


def _desiredSort(tabName, fields):
	"""Return (field, reverse) to apply to the given tab, or None to leave NVDA's choice."""
	if _conf()["mode"] == MODE_REMEMBER:
		saved = _parseRemembered().get(_rememberKey(tabName))
		if saved:
			field = _listField(saved[0])
			if field is not None and field in fields:
				return field, saved[1]
			# Remembered field does not exist on this tab (e.g. install date on Available add-ons);
			# fall through to the configured default for this tab.
	return _fixedSortFor(tabName, fields)


def _tabName(dialog):
	return dialog._statusFilterKey.name


def _prepareTabChange(dialog):
	"""Run before NVDA's own tab change handler.

	NVDA 2026.2+ keeps the sort field across tabs and looks up its position in the
	new tab's column list. A field missing on the new tab (install date on the Available tab)
	would make that lookup fail, so temporarily switch to a field present on every tab.
	"""
	listVM = dialog._storeVM.listVM
	if not hasattr(listVM, "_prevSortByModelField"):
		return
	from gui.addonStoreGui.viewModels.addonList import AddonListField

	newKey = dialog._statusFilterKey
	oldKey = dialog._storeVM._filteredStatusKey

	def validEverywhere(field):
		# Relevance is always selectable; other fields must be visible on both tabs.
		if field.name == "searchRank":
			return True
		return newKey not in field.hideStatuses and oldKey not in field.hideStatuses

	safe = _listField("publicationDate") or AddonListField.displayName
	if not validEverywhere(listVM._sortByModelField):
		listVM._sortByModelField = safe
	if not validEverywhere(listVM._prevSortByModelField):
		listVM._prevSortByModelField = safe


def _applySort(dialog):
	listVM = dialog._storeVM.listVM
	fields = _choiceFields(listVM)
	desired = _desiredSort(_tabName(dialog), fields)
	if desired is None:
		# Keep NVDA behaviour, but make sure the combo box matches the actual sort
		# (relevant after _prepareTabChange changed it).
		field = listVM._sortByModelField
		if field in fields:
			reverse = bool(getattr(listVM, "_reverseSort", False))
			dialog.columnFilterCtrl.SetSelection(fields.index(field) * 2 + (1 if reverse else 0))
		return
	field, reverse = desired
	listVM.setSortField(field, reverse)
	# The sort restored after clearing the search field (NVDA 2026.2+).
	if hasattr(listVM, "_prevSortByModelField"):
		listVM._prevSortByModelField = field
	if hasattr(listVM, "_prevReverseSort"):
		listVM._prevReverseSort = reverse
	dialog.columnFilterCtrl.SetSelection(fields.index(field) * 2 + (1 if reverse else 0))


def _recordSort(dialog):
	"""Save the sort the user has just chosen."""
	conf = _conf()
	if not conf["enabled"] or conf["mode"] != MODE_REMEMBER:
		return
	listVM = dialog._storeVM.listVM
	field = listVM._sortByModelField
	if field.name == "searchRank":
		# Relevance only makes sense while searching; don't remember it.
		return
	data = _parseRemembered()
	data[_rememberKey(_tabName(dialog))] = (field.name, bool(getattr(listVM, "_reverseSort", False)))
	_storeRemembered(data)


def _recordTab(dialog):
	_conf()["lastTab"] = _tabName(dialog)


def _openTabFor(requested):
	"""Return the _StatusFilterKey the store should open on, or requested to keep NVDA's choice."""
	conf = _conf()
	if not conf["enabled"]:
		return requested
	if requested is not None and not conf["openTabOverridesUpdates"]:
		# NVDA asked for a specific tab (e.g. "Updatable add-ons" from the update notification).
		return requested
	choice = conf["openTab"]
	if choice == OPEN_NVDA:
		return requested
	if choice == OPEN_LAST:
		choice = conf["lastTab"]
	from addonStore.models.status import _StatusFilterKey

	return getattr(_StatusFilterKey, choice, None) if choice in TABS else requested


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super().__init__()
		self._patched = []
		if globalVars.appArgs.secure:
			return
		settingsDialogs.NVDASettingsDialog.categoryClasses.append(SortMemorySettingsPanel)
		try:
			self._patch()
		except Exception:
			log.exception("Add-on Store Sort Memory: could not attach to the Add-on Store")

	def _wrap(self, cls, name, before=None, after=None, getDialog=lambda obj: obj):
		original = getattr(cls, name)

		@functools.wraps(original)
		def wrapper(obj, *args, **kwargs):
			active = _conf()["enabled"]
			if active and before:
				try:
					before(getDialog(obj))
				except Exception:
					log.exception("Add-on Store Sort Memory: error before %s" % name)
			result = original(obj, *args, **kwargs)
			if active and after:
				try:
					after(getDialog(obj))
				except Exception:
					log.exception("Add-on Store Sort Memory: error after %s" % name)
			return result

		setattr(cls, name, wrapper)
		self._patched.append((cls, name, original))

	def _wrapInit(self, cls):
		"""Choose the tab the Add-on Store opens on (the openToTab argument of the dialog)."""
		original = cls.__init__

		@functools.wraps(original)
		def wrapper(obj, parent, storeVM, *args, **kwargs):
			if args:
				requested, args = args[0], args[1:]
			else:
				requested = kwargs.pop("openToTab", None)
			try:
				requested = _openTabFor(requested)
			except Exception:
				log.exception("Add-on Store Sort Memory: error choosing the opening tab")
			return original(obj, parent, storeVM, requested, *args, **kwargs)

		cls.__init__ = wrapper
		self._patched.append((cls, "__init__", original))

	def _patch(self):
		from gui.addonStoreGui.controls.storeDialog import AddonStoreDialog
		from gui.addonStoreGui.controls.addonList import AddonVirtualList

		# Bindings are made with self.onListTabPageChange etc. when the dialog is created,
		# so replacing the class attributes covers every dialog opened from now on.
		self._wrap(AddonStoreDialog, "onListTabPageChange", before=_prepareTabChange, after=_applySort)
		self._wrap(AddonStoreDialog, "onListTabPageChange", after=_recordTab)
		self._wrapInit(AddonStoreDialog)
		self._wrap(AddonStoreDialog, "onColumnFilterChange", after=_recordSort)
		if hasattr(AddonVirtualList, "OnColClick"):
			# Sorting by clicking a column header.
			self._wrap(AddonVirtualList, "OnColClick", after=_recordSort, getDialog=lambda lst: lst.Parent)

	def terminate(self):
		for cls, name, original in reversed(self._patched):
			setattr(cls, name, original)
		self._patched = []
		try:
			settingsDialogs.NVDASettingsDialog.categoryClasses.remove(SortMemorySettingsPanel)
		except ValueError:
			pass
		super().terminate()


def _tabLabels():
	"""Tab names as NVDA shows them, translated by NVDA itself."""
	labels = {}
	try:
		from addonStore.models.status import _StatusFilterKey

		for tab in TABS:
			labels[tab] = getattr(_StatusFilterKey, tab).displayString
	except Exception:
		pass
	fallback = {
		# Translators: Name of a tab in the Add-on Store (fallback if NVDA's own name is unavailable).
		"INSTALLED": _("Installed add-ons"),
		# Translators: Name of a tab in the Add-on Store (fallback if NVDA's own name is unavailable).
		"UPDATE": _("Updatable add-ons"),
		# Translators: Name of a tab in the Add-on Store (fallback if NVDA's own name is unavailable).
		"AVAILABLE": _("Available add-ons"),
		# Translators: Name of a tab in the Add-on Store (fallback if NVDA's own name is unavailable).
		"INCOMPATIBLE": _("Incompatible add-ons"),
	}
	for tab in TABS:
		labels.setdefault(tab, fallback[tab])
	return labels


class SortMemorySettingsPanel(settingsDialogs.SettingsPanel):
	# Translators: Title of the settings category of this add-on in NVDA settings.
	title = _("Add-on Store Sort Memory")

	def makeSettings(self, settingsSizer):
		conf = _conf()
		helper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		self.enabledCheck = helper.addItem(
			# Translators: Checkbox in the settings of this add-on.
			wx.CheckBox(self, label=_("&Manage sorting of the Add-on Store list")),
		)
		self.enabledCheck.SetValue(conf["enabled"])
		self.enabledCheck.Bind(wx.EVT_CHECKBOX, self._updateState)

		self._modeValues = [MODE_REMEMBER, MODE_FIXED]
		modeLabels = [
			# Translators: A sorting mode in the settings of this add-on.
			_("Remember the last sort I chose"),
			# Translators: A sorting mode in the settings of this add-on.
			_("Always use the default sort below"),
		]
		self.modeChoice = helper.addLabeledControl(
			# Translators: Label of a combo box in the settings of this add-on.
			_("Sorting m&ode:"),
			wx.Choice,
			choices=modeLabels,
		)
		self.modeChoice.SetSelection(self._modeValues.index(conf["mode"]))
		self.modeChoice.Bind(wx.EVT_CHOICE, self._updateState)

		self.perTabCheck = helper.addItem(
			# Translators: Checkbox in the settings of this add-on.
			wx.CheckBox(self, label=_("Remember sorting separately for each &tab")),
		)
		self.perTabCheck.SetValue(conf["rememberPerTab"])

		sortLabels = {
			# Translators: A sort option in the settings of this add-on.
			SORT_NVDA: _("NVDA default (do not change)"),
			# Translators: A sort option in the settings of this add-on.
			SORT_PUB_NEWEST: _("Publication date, newest first"),
			# Translators: A sort option in the settings of this add-on.
			SORT_PUB_OLDEST: _("Publication date, oldest first"),
			# Translators: A sort option in the settings of this add-on.
			SORT_INSTALL_NEWEST: _("Install date, newest first"),
			# Translators: A sort option in the settings of this add-on.
			SORT_INSTALL_OLDEST: _("Install date, oldest first"),
		}
		tabLabels = _tabLabels()
		self.tabChoices = {}
		for tab in TABS:
			values = [v for v in _SORT_VALUES if tab in TABS_WITH_INSTALL_DATE or v not in _INSTALL_SORTS]
			ctrl = helper.addLabeledControl(
				# Translators: Label of a combo box in the settings of this add-on;
				# {tab} is the name of a tab in the Add-on Store, e.g. "Available add-ons".
				_("Default sort for {tab}:").format(tab=tabLabels[tab]),
				wx.Choice,
				choices=[sortLabels[v] for v in values],
			)
			current = conf["sort" + tab]
			ctrl.SetSelection(values.index(current) if current in values else values.index(SORT_PUB_NEWEST))
			self.tabChoices[tab] = (ctrl, values)

		self._openValues = [OPEN_NVDA, OPEN_LAST] + list(TABS)
		openLabels = [
			# Translators: An option for the tab opened with the Add-on Store.
			_("NVDA default (Installed add-ons, or Available if none are installed)"),
			# Translators: An option for the tab opened with the Add-on Store.
			_("Last used tab"),
		] + [tabLabels[tab] for tab in TABS]
		self.openTabChoice = helper.addLabeledControl(
			# Translators: Label of a combo box in the settings of this add-on.
			_("Tab to &open when entering the Add-on Store:"),
			wx.Choice,
			choices=openLabels,
		)
		self.openTabChoice.SetSelection(self._openValues.index(conf["openTab"]))
		self.openTabChoice.Bind(wx.EVT_CHOICE, self._updateState)

		self.overrideUpdatesCheck = helper.addItem(
			wx.CheckBox(
				self,
				# Translators: Checkbox in the settings of this add-on.
				label=_("Use this tab also when NVDA opens the store to show add-on &updates"),
			),
		)
		self.overrideUpdatesCheck.SetValue(conf["openTabOverridesUpdates"])

		self.forgetButton = helper.addItem(
			# Translators: Button in the settings of this add-on.
			wx.Button(self, label=_("&Forget remembered sorting")),
		)
		self.forgetButton.Bind(wx.EVT_BUTTON, self._onForget)
		self._updateState()

	def _updateState(self, evt=None):
		enabled = self.enabledCheck.GetValue()
		remember = self._modeValues[self.modeChoice.GetSelection()] == MODE_REMEMBER
		self.modeChoice.Enable(enabled)
		self.perTabCheck.Enable(enabled and remember)
		self.forgetButton.Enable(enabled and remember)
		for ctrl, values in self.tabChoices.values():
			ctrl.Enable(enabled)
		self.openTabChoice.Enable(enabled)
		openNvda = self._openValues[self.openTabChoice.GetSelection()] == OPEN_NVDA
		self.overrideUpdatesCheck.Enable(enabled and not openNvda)

	def _onForget(self, evt):
		_conf()["remembered"] = ""
		gui.messageBox(
			# Translators: Message shown after the remembered sorting was cleared.
			_("Remembered sorting has been cleared. The default sort will be used next time."),
			# Translators: Title of a message box.
			_("Add-on Store Sort Memory"),
			wx.OK | wx.ICON_INFORMATION,
			self,
		)

	def onSave(self):
		conf = _conf()
		conf["enabled"] = self.enabledCheck.GetValue()
		conf["mode"] = self._modeValues[self.modeChoice.GetSelection()]
		if conf["rememberPerTab"] != self.perTabCheck.GetValue():
			# Stored keys differ between shared and per-tab memory.
			conf["remembered"] = ""
		conf["rememberPerTab"] = self.perTabCheck.GetValue()
		for tab, (ctrl, values) in self.tabChoices.items():
			conf["sort" + tab] = values[ctrl.GetSelection()]
		conf["openTab"] = self._openValues[self.openTabChoice.GetSelection()]
		conf["openTabOverridesUpdates"] = self.overrideUpdatesCheck.GetValue()
