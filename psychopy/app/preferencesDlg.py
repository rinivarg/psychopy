#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function

import json
from builtins import str
import wx
import wx.propgrid as pg
import wx.py
import platform
import re
import os

from . import dialogs
from psychopy import localization, prefs
from psychopy.localization import _translate
from pkg_resources import parse_version
from psychopy import sound
from psychopy.app.utils import getSystemFonts
import collections

# labels mappings for display:
_localized = {
    # section labels:
    'general': _translate('General'),
    'app': _translate('App'),
    'builder': "Builder",  # not localized
    'coder': "Coder",  # not localized
    'hardware': _translate('Hardware'),
    'connections': _translate('Connections'),
    'keyBindings': _translate('Key bindings'),
    # pref labels:
    'winType': _translate("window type"),
    'units': _translate("units"),
    'fullscr': _translate("full-screen"),
    'allowGUI': _translate("allow GUI"),
    'paths': _translate('paths'),
    'audioLib': _translate("audio library"),
    'audioDriver': _translate("audio driver"),
    'audioDevice': _translate("audio device"),
    'audioLatencyMode': _translate("audio latency mode"),
    'flac': _translate('flac audio compression'),
    'parallelPorts': _translate("parallel ports"),
    'qmixConfiguration': _translate("Qmix configuration"),
    'shutdownKey': _translate("shutdown key"),
    'shutdownKeyModifiers': _translate("shutdown key modifier keys"),
    'showStartupTips': _translate("show start-up tips"),
    'largeIcons': _translate("large icons"),
    'defaultView': _translate("default view"),
    'darkMode': _translate("dark mode"),
    'resetPrefs': _translate('reset preferences'),
    'autoSavePrefs': _translate('auto-save prefs'),
    'debugMode': _translate('debug mode'),
    'locale': _translate('locale'),
    'readonly': _translate('read-only'),
    'codeFont': _translate('code font'),
    'commentFont': _translate('comment font'),
    'outputFont': _translate('output font'),
    'outputFontSize': _translate('output font size'),
    'codeFontSize': _translate('code font size'),
    'showSourceAsst': _translate('show source asst'),
    'showOutput': _translate('show output'),
    'reloadPrevFiles': _translate('reload previous files'),
    'preferredShell': _translate('preferred shell'),
    'reloadPrevExp': _translate('reload previous exp'),
    'unclutteredNamespace': _translate('uncluttered namespace'),
    'componentsFolders': _translate('components folders'),
    'hiddenComponents': _translate('hidden components'),
    'unpackedDemosDir': _translate('unpacked demos dir'),
    'savedDataFolder': _translate('saved data folder'),
    'topFlow': _translate('Flow at top'),
    'alwaysShowReadme': _translate('always show readme'),
    'maxFavorites': _translate('max favorites'),
    'proxy': _translate('proxy'),
    'autoProxy': _translate('auto-proxy'),
    'allowUsageStats': _translate('allow usage stats'),
    'checkForUpdates': _translate('check for updates'),
    'timeout': _translate('timeout'),
    'open': _translate('open'),
    'new': _translate('new'),
    'save': _translate('save'),
    'saveAs': _translate('save as'),
    'print': _translate('print'),
    'close': _translate('close'),
    'quit': _translate('quit'),
    'preferences': _translate('preferences'),
    'exportHTML': _translate('export HTML'),
    'cut': _translate('cut'),
    'copy': _translate('copy'),
    'paste': _translate('paste'),
    'duplicate': _translate('duplicate'),
    'indent': _translate('indent'),
    'dedent': _translate('dedent'),
    'smartIndent': _translate('smart indent'),
    'find': _translate('find'),
    'findAgain': _translate('find again'),
    'undo': _translate('undo'),
    'redo': _translate('redo'),
    'comment': _translate('comment'),
    'uncomment': _translate('uncomment'),
    'toggle comment': _translate('toggle comment'),
    'fold': _translate('fold'),
    'enlargeFont': _translate('enlarge Font'),
    'shrinkFont': _translate('shrink Font'),
    'analyseCode': _translate('analyze code'),
    'compileScript': _translate('compile script'),
    'runScript': _translate('run script'),
    'stopScript': _translate('stop script'),
    'toggleWhitespace': _translate('toggle whitespace'),
    'toggleEOLs': _translate('toggle EOLs'),
    'toggleIndentGuides': _translate('toggle indent guides'),
    'newRoutine': _translate('new Routine'),
    'copyRoutine': _translate('copy Routine'),
    'pasteRoutine': _translate('paste Routine'),
    'pasteCompon': _translate('paste Component'),
    'toggleOutputPanel': _translate('toggle output panel'),
    'renameRoutine': _translate('rename Routine'),
    'switchToBuilder': _translate('switch to Builder'),
    'switchToCoder': _translate('switch to Coder'),
    'switchToRunner': _translate('switch to Runner'),
    'largerFlow': _translate('larger Flow'),
    'smallerFlow': _translate('smaller Flow'),
    'largerRoutine': _translate('larger routine'),
    'smallerRoutine': _translate('smaller routine'),
    'toggleReadme': _translate('toggle readme'),
    'projectsLogIn': _translate('login to projects'),
    'pavlovia_logIn': _translate('login to pavlovia'),
    'OSF_logIn': _translate('login to OSF'),
    'projectsSync': _translate('sync projects'),
    'projectsFind': _translate('find projects'),
    'projectsOpen': _translate('open projects'),
    'projectsNew': _translate('new projects'),
    # pref wxChoice lists:
    'last': _translate('same as last session'),
    'both': _translate('both Builder & Coder'),
    'keep': _translate('same as in the file'),  # line endings
    # not translated:
    'pix': 'pix',
    'deg': 'deg',
    'cm': 'cm',
    'norm': 'norm',
    'height': 'height',
    'pyshell': 'pyshell',
    'iPython': 'iPython'
}
# add pre-translated names-of-langauges, for display in locale pref:
_localized.update(localization.locname)

audioLatencyLabels = {0: _translate('Latency not important'),
                      1: _translate('Share low-latency driver'),
                      2: _translate('Exclusive low-latency'),
                      3: _translate('Aggressive low-latency'),
                      4: _translate('Latency critical')}


class PrefPropGrid(wx.Panel):
    """Class for the property grid portion of the preference window."""

    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.TAB_TRAVERSAL,
                 name=wx.EmptyString):
        wx.Panel.__init__(
            self, parent, id=id, pos=pos, size=size, style=style, name=name)
        bSizer1 = wx.BoxSizer(wx.HORIZONTAL)
        self.app = wx.GetApp()

        self.lstPrefPages = wx.ListCtrl(
            self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
            wx.LC_ALIGN_TOP | wx.LC_ICON | wx.LC_SINGLE_SEL)
        bSizer1.Add(self.lstPrefPages, 0,
                    wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.TOP, 5)

        prefsImageSize = wx.Size(48, 48)
        self.prefsIndex = 0
        self.prefsImages = wx.ImageList(
            prefsImageSize.GetWidth(), prefsImageSize.GetHeight())
        self.lstPrefPages.AssignImageList(self.prefsImages, wx.IMAGE_LIST_NORMAL)

        self.proPrefs = pg.PropertyGridManager(
            self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
            wx.propgrid.PGMAN_DEFAULT_STYLE | wx.propgrid.PG_BOLD_MODIFIED |
            wx.propgrid.PG_DESCRIPTION | wx.TAB_TRAVERSAL)
        self.proPrefs.SetExtraStyle(wx.propgrid.PG_EX_MODE_BUTTONS)

        bSizer1.Add(self.proPrefs, 1, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(bSizer1)
        self.Layout()

        # Connect Events
        self.lstPrefPages.Bind(
            wx.EVT_LIST_ITEM_DESELECTED, self.OnPrefPageDeselected)
        self.lstPrefPages.Bind(
            wx.EVT_LIST_ITEM_SELECTED, self.OnPrefPageSelected)
        self.proPrefs.Bind(pg.EVT_PG_CHANGED, self.OnPropPageChanged)
        self.proPrefs.Bind(pg.EVT_PG_CHANGING, self.OnPropPageChanging)

        # categories and their items are stored here
        self.sections = collections.OrderedDict()

        # pages in the property manager
        self.pages = dict()
        self.pageNames = dict()

        # help text
        self.helpText = dict()

        self.pageIdx = 0

    def __del__(self):
        pass

    def setSelection(self, page):
        """Select the page."""
        # set the page
        self.lstPrefPages.Focus(1)
        self.lstPrefPages.Select(page)

    def addPage(self, label, name, sections=(), bitmap=None):
        """Add a page to the property grid manager."""

        if name in self.pages.keys():
            raise ValueError("Page already exists.")

        for s in sections:
            if s not in self.sections.keys():
                self.sections[s] = dict()

        nbBitmap = self.app.iconCache.getBitmap(bitmap)
        if nbBitmap.IsOk():
            self.prefsImages.Add(nbBitmap)

        self.pages[self.pageIdx] = (self.proPrefs.AddPage(name, wx.NullBitmap),
                                    list(sections))
        self.pageNames[name] = self.pageIdx
        self.lstPrefPages.InsertItem(
            self.lstPrefPages.GetItemCount(), label, self.pageIdx)

        self.pageIdx += 1

    def addStringItem(self, section, label=wx.propgrid.PG_LABEL,
                      name=wx.propgrid.PG_LABEL, value='', helpText=""):
        """Add a string property to a category.

        Parameters
        ----------
        section : str
            Category name to add the item too.
        label : str
            Label to be displayed in the property grid.
        name : str
            Internal name for the property.
        value : str
            Default value for the property.
        helpText: str
            Help text for this item.

        """
        # create a new category if not present
        if section not in self.sections.keys():
            self.sections[section] = dict()

        # if isinstance(page, str):
        #     page = self.proPrefs.GetPageByName(page)
        # else
        #     page = self.proPrefs.GetPage(page)
        self.sections[section].update(
            {name: wx.propgrid.StringProperty(label, name, value=str(value))})

        self.helpText[name] = helpText

    def addStringArrayItem(self, section, label=wx.propgrid.PG_LABEL,
                           name=wx.propgrid.PG_LABEL, values=(), helpText=""):
        """Add a string array item."""
        if section not in self.sections.keys():
            self.sections[section] = dict()

        self.sections[section].update(
            {name: wx.propgrid.ArrayStringProperty(
                label, name, value=[str(i) for i in values])})

        self.helpText[name] = helpText

    def addBoolItem(self, section, label=wx.propgrid.PG_LABEL,
                    name=wx.propgrid.PG_LABEL, value=False, helpText=""):
        if section not in self.sections.keys():
            self.sections[section] = dict()

        self.sections[section].update(
            {name: wx.propgrid.BoolProperty(label, name, value)})

        self.helpText[name] = helpText

    def addFileItem(self, section, label=wx.propgrid.PG_LABEL,
                    name=wx.propgrid.PG_LABEL, value='', helpText=""):
        if section not in self.sections.keys():
            self.sections[section] = []

        self.sections[section].update(
            {name: wx.propgrid.FileProperty(label, name, value)})

        self.helpText[name] = helpText

    def addDirItem(self, section, label=wx.propgrid.PG_LABEL,
                    name=wx.propgrid.PG_LABEL, value='', helpText=""):
        if section not in self.sections.keys():
            self.sections[section] = dict()

        self.sections[section].update(
            {name: wx.propgrid.DirProperty(label, name, value)})

        self.helpText[name] = helpText

    def addIntegerItem(self, section, label=wx.propgrid.PG_LABEL,
                       name=wx.propgrid.PG_LABEL, value=0, helpText=""):
        """Add an integer property to a category.

        Parameters
        ----------
        section : str
            Category name to add the item too.
        label : str
            Label to be displayed in the property grid.
        name : str
            Internal name for the property.
        value : int
            Default value for the property.
        helpText: str
            Help text for this item.

        """
        if section not in self.sections.keys():
            self.sections[section] = dict()

        self.sections[section].update(
            {name: wx.propgrid.IntProperty(label, name, value=int(value))})

        self.helpText[name] = helpText

    def addEnumItem(self, section, label=wx.propgrid.PG_LABEL,
                    name=wx.propgrid.PG_LABEL, labels=(), values=(), value=0,
                    helpText=""):
        if section not in self.sections.keys():
            self.sections[section] = dict()

        self.sections[section].update({
            name: wx.propgrid.EnumProperty(label, name, labels, values, value)})

        self.helpText[name] = helpText

    def populateGrid(self):
        """Go over pages and add items to the property grid."""
        for i in range(self.proPrefs.GetPageCount()):
            pagePtr, sections = self.pages[i]
            pagePtr.Clear()

            for s in sections:
                _ = pagePtr.Append(pg.PropertyCategory(s, s))
                for name, prop in self.sections[s].items():
                    item = pagePtr.Append(prop)

                    # set the appropriate control to edit the attribute
                    if isinstance(prop, wx.propgrid.IntProperty):
                        self.proPrefs.SetPropertyEditor(item, "SpinCtrl")
                    elif isinstance(prop, wx.propgrid.BoolProperty):
                        self.proPrefs.SetPropertyAttribute(
                            item, "UseCheckbox", True)
                    try:
                        self.proPrefs.SetPropertyHelpString(
                            item, self.helpText[item.GetName()])
                    except KeyError:
                        pass

        self.proPrefs.SetSplitterLeft()
        self.setSelection(0)

    def setPrefVal(self, section, name, value):
        """Set the value of a preference."""
        try:
            self.sections[section][name].SetValue(value)
            return True
        except KeyError:
            return False

    def getPrefVal(self, section, name):
        """Get the value of a preference."""
        try:
            return self.sections[section][name].GetValue()
        except KeyError:
            return None

    def OnPrefPageDeselected(self, event):
        event.Skip()

    def OnPrefPageSelected(self, event):
        sel = self.lstPrefPages.GetFirstSelected()

        if sel >= 0:
            self.proPrefs.SelectPage(sel)

        event.Skip()

    def OnPropPageChanged(self, event):
        event.Skip()

    def OnPropPageChanging(self, event):
        event.Skip()

    def isModified(self):
        return self.proPrefs.IsAnyModified()


class PreferencesDlg(wx.Dialog):
    """Class for a dialog which edits PsychoPy's preferences.
    """
    def __init__(self, app):
        wx.Dialog.__init__(
            self, None, id=wx.ID_ANY, title=u"PsychoPy Preferences",
            pos=wx.DefaultPosition, size=wx.Size(800, 600),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.app = app
        self.prefsCfg = self.app.prefs.userPrefsCfg
        self.prefsSpec = self.app.prefs.prefsSpec

        self._pages = {}  # property grids for each page

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        sbMain = wx.BoxSizer(wx.VERTICAL)

        self.pnlMain = wx.Panel(
            self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
            wx.TAB_TRAVERSAL)
        sbPrefs = wx.BoxSizer(wx.VERTICAL)

        self.proPrefs = PrefPropGrid(
            self.pnlMain, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
            wx.LB_DEFAULT)

        # add property pages to the manager
        self.proPrefs.addPage(
            'General', 'general', ['general'],
            'preferences-general48.png')
        self.proPrefs.addPage(
            'Application', 'app', ['app', 'builder', 'coder'],
            'preferences-app48.png')
        self.proPrefs.addPage(
            'Key Bindings', 'keyBindings', ['keyBindings'],
            'preferences-keyboard48.png')
        self.proPrefs.addPage(
            'Hardware', 'hardware', ['hardware'], 'preferences-hardware48.png')
        self.proPrefs.addPage(
            'Connections', 'connections', ['connections'],
            'preferences-conn48.png')
        self.proPrefs.populateGrid()

        sbPrefs.Add(self.proPrefs, 1, wx.EXPAND)

        self.stlMain = wx.StaticLine(
            self.pnlMain, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
            wx.LI_HORIZONTAL)
        sbPrefs.Add(self.stlMain, 0, wx.EXPAND | wx.ALL, 5)

        # dialog controls, have builtin localization
        sdbControls = wx.StdDialogButtonSizer()
        self.sdbControlsHelp = wx.Button(self.pnlMain, wx.ID_HELP)
        sdbControls.AddButton(self.sdbControlsHelp)
        self.sdbControlsApply = wx.Button(self.pnlMain, wx.ID_APPLY)
        sdbControls.AddButton(self.sdbControlsApply)
        self.sdbControlsOK = wx.Button(self.pnlMain, wx.ID_OK)
        sdbControls.AddButton(self.sdbControlsOK)
        self.sdbControlsCancel = wx.Button(self.pnlMain, wx.ID_CANCEL)
        sdbControls.AddButton(self.sdbControlsCancel)

        sdbControls.Realize()

        sbPrefs.Add(sdbControls, 0, wx.ALL | wx.ALIGN_RIGHT, 0)

        self.pnlMain.SetSizer(sbPrefs)
        self.pnlMain.Layout()
        sbPrefs.Fit(self.pnlMain)
        sbMain.Add(self.pnlMain, 1, wx.EXPAND | wx.ALL, 8)

        self.SetSizer(sbMain)
        self.Layout()

        self.Centre(wx.BOTH)

        # Connect Events
        self.sdbControlsApply.Bind(wx.EVT_BUTTON, self.OnApplyClicked)
        self.sdbControlsCancel.Bind(wx.EVT_BUTTON, self.OnCancelClicked)
        self.sdbControlsHelp.Bind(wx.EVT_BUTTON, self.OnHelpClicked)
        self.sdbControlsOK.Bind(wx.EVT_BUTTON, self.OnOKClicked)

        # system fonts for font properties
        self.fontList = ['From theme...'] + list(getSystemFonts(fixedWidthOnly=True))

        # valid themes
        themePath = self.GetTopLevelParent().app.prefs.paths['themes']
        self.themeList = []
        for themeFile in os.listdir(themePath):
            try:
                # Load theme from json file
                with open(os.path.join(themePath, themeFile), "rb") as fp:
                    theme = json.load(fp)
                # Add themes to list only if min spec is defined
                base = theme['base']
                if all(key in base for key in ['bg', 'fg', 'font']):
                    self.themeList += [themeFile.replace('.json', '')]
            except:
                pass

        # get sound devices for "audioDevice" property
        try:
            devnames = sorted(sound.getDevices('output'))
        except (ValueError, OSError, ImportError):
            devnames = []

        audioConf = self.prefsCfg['hardware']['audioDevice']
        self.audioDevDefault = audioConf \
            if type(audioConf) != list else list(audioConf)
        self.audioDevNames = [
            dev.replace('\r\n', '') for dev in devnames
            if dev != self.audioDevDefault]

        self.populatePrefs()

    def __del__(self):
        pass

    def populatePrefs(self):
        """Populate pages with property items for each preference."""
        # clear pages
        for sectionName in self.prefsSpec.keys():
            prefsSection = self.prefsCfg[sectionName]
            specSection = self.prefsSpec[sectionName]

            for prefName in specSection:
                if prefName in ['version']:  # any other prefs not to show?
                    continue
                # allowModuleImports pref is handled by generateSpec.py
                # NB if something is in prefs but not in spec then it won't be
                # shown (removes outdated prefs)
                thisPref = prefsSection[prefName]
                thisSpec = specSection[prefName]

                # for keybindings replace Ctrl with Cmd on Mac
                if platform.system() == 'Darwin' and \
                        sectionName == 'keyBindings':
                    if thisSpec.startswith('string'):
                        thisPref = thisPref.replace('Ctrl+', 'Cmd+')

                # can we translate this pref?
                try:
                    pLabel = _localized[prefName]
                except Exception:
                    pLabel = prefName

                # get tooltips from comment lines from the spec, as parsed by
                # configobj
                helpText = ''
                hints = self.prefsSpec[sectionName].comments[prefName]  # a list
                if len(hints):
                    # use only one comment line, from right above the pref
                    hint = hints[-1].lstrip().lstrip('#').lstrip()
                    helpText = _translate(hint)

                if type(thisPref) == bool:
                    # only True or False - use a checkbox
                    self.proPrefs.addBoolItem(
                        sectionName, pLabel, prefName, thisPref,
                        helpText=helpText)

                # # properties for fonts, dropdown gives a list of system fonts
                elif prefName in ('codeFont', 'commentFont', 'outputFont'):
                    try:
                        default = self.fontList.index(thisPref)
                    except ValueError:
                        default = 0
                    self.proPrefs.addEnumItem(
                            sectionName,
                            pLabel,
                            prefName,
                            labels=self.fontList,
                            values=[i for i in range(len(self.fontList))],
                            value=default, helpText=helpText)
                elif prefName in ('theme',):
                    try:
                        default = self.themeList.index(thisPref)
                    except ValueError:
                        default = self.themeList.index("PsychopyLight")
                    self.proPrefs.addEnumItem(
                            sectionName,
                            pLabel,
                            prefName,
                            labels=self.themeList,
                            values=[i for i in range(len(self.themeList))],
                            value=default, helpText=helpText)
                elif prefName == 'locale':
                    thisPref = self.app.prefs.app['locale']
                    locales = self.app.localization.available
                    try:
                        default = locales.index(thisPref)
                    except ValueError:
                        # default to US english
                        default = locales.index('en_US')
                    self.proPrefs.addEnumItem(
                            sectionName,
                            pLabel,
                            prefName,
                            labels=[_localized[i] for i in locales],
                            values=[i for i in range(len(locales))],
                            value=default, helpText=helpText)
                # # single directory
                elif prefName in ('unpackedDemosDir',):
                    self.proPrefs.addDirItem(
                        sectionName, pLabel, prefName, thisPref,
                        helpText=helpText)
                # single file
                elif prefName in ('flac',):
                    self.proPrefs.addFileItem(
                        sectionName, pLabel, prefName, thisPref,
                        helpText=helpText)
                # # audio latency mode for the PTB driver
                elif prefName == 'audioLatencyMode':
                    # get the labels from above
                    labels = []
                    for val, labl in audioLatencyLabels.items():
                        labels.append(u'{}: {}'.format(val, labl))

                    # get the options from the config file spec
                    vals = thisSpec.replace("option(", "").replace("'", "")
                    # item -1 is 'default=x' from spec
                    vals = vals.replace(", ", ",").split(',')

                    try:
                        # set the field to the value in the pref
                        default = int(thisPref)
                    except ValueError:
                        try:
                            # use first if default not in list
                            default = int(vals[-1].strip('()').split('=')[1])
                        except (IndexError, TypeError, ValueError):
                            # no default
                            default = 0

                    self.proPrefs.addEnumItem(
                            sectionName,
                            pLabel,
                            prefName,
                            labels=labels,
                            values=[i for i in range(len(labels))],
                            value=default, helpText=helpText)
                # # option items are given a dropdown, current value is shown
                # # in the box
                elif thisSpec.startswith('option') or prefName == 'audioDevice':
                    if prefName == 'audioDevice':
                        options = self.audioDevNames
                        try:
                            default = self.audioDevNames.index(
                                self.audioDevDefault)
                        except ValueError:
                            default = 0
                    else:
                        vals = thisSpec.replace("option(", "").replace("'", "")
                        # item -1 is 'default=x' from spec
                        vals = vals.replace(", ", ",").split(',')
                        options = vals[:-1]
                        try:
                            # set the field to the value in the pref
                            default = options.index(thisPref)
                        except ValueError:
                            try:
                                # use first if default not in list
                                default = vals[-1].strip('()').split('=')[1]
                            except IndexError:
                                # no default
                                default = 0

                    labels = []  # display only
                    for opt in options:
                        try:
                            labels.append(_localized[opt])
                        except Exception:
                            labels.append(opt)

                    self.proPrefs.addEnumItem(
                            sectionName,
                            pLabel,
                            prefName,
                            labels=labels,
                            values=[i for i in range(len(labels))],
                            value=default, helpText=helpText)
                # # lists are given a property that can edit and reorder items
                elif thisSpec.startswith('list'):  # list
                    self.proPrefs.addStringArrayItem(
                        sectionName, pLabel, prefName,
                        [str(i) for i in thisPref], helpText)
                # integer items
                elif thisSpec.startswith('integer'):  # integer
                    self.proPrefs.addIntegerItem(
                        sectionName, pLabel, prefName, thisPref, helpText)
                # # all other items just use a string field
                else:
                    self.proPrefs.addStringItem(
                        sectionName, pLabel, prefName, thisPref, helpText)

        self.proPrefs.populateGrid()

    def applyPrefs(self):
        """Write preferences to the current configuration."""
        if not self.proPrefs.isModified():
            return

        if platform.system() == 'Darwin':
            re_cmd2ctrl = re.compile('^Cmd\+', re.I)

        for sectionName in self.prefsSpec:
            for prefName in self.prefsSpec[sectionName]:
                if prefName in ['version']:  # any other prefs not to show?
                    continue

                thisPref = self.proPrefs.getPrefVal(sectionName, prefName)
                # handle special cases
                if prefName in ('codeFont', 'commentFont', 'outputFont'):
                    self.prefsCfg[sectionName][prefName] = \
                        self.fontList[thisPref]
                    continue
                if prefName in ('theme',):
                    self.prefsCfg[sectionName][prefName] = \
                        self.themeList[thisPref]
                    continue
                elif prefName == 'audioDevice':
                    self.prefsCfg[sectionName][prefName] = \
                        self.audioDevNames[thisPref]
                    continue
                elif prefName == 'locale':
                    # fake spec -> option: use available locale info not spec file
                    self.app.prefs.app['locale'] = \
                        self.app.localization.available[thisPref]
                    self.prefsCfg[sectionName][prefName] = \
                        self.app.localization.available[thisPref]
                    continue

                # remove invisible trailing whitespace:
                if hasattr(thisPref, 'strip'):
                    thisPref = thisPref.strip()
                # regularize the display format for keybindings
                if sectionName == 'keyBindings':
                    thisPref = thisPref.replace(' ', '')
                    thisPref = '+'.join([part.capitalize()
                                         for part in thisPref.split('+')])
                    if platform.system() == 'Darwin':
                        # key-bindings were displayed as 'Cmd+O', revert to
                        # 'Ctrl+O' internally
                        thisPref = re_cmd2ctrl.sub('Ctrl+', thisPref)
                self.prefsCfg[sectionName][prefName] = thisPref

                # make sure list values are converted back to lists (from str)
                if self.prefsSpec[sectionName][prefName].startswith('list'):
                    try:
                        # if thisPref is not a null string, do eval() to get a
                        # list.
                        if thisPref == '' or type(thisPref) == list:
                            newVal = thisPref
                        else:
                            newVal = eval(thisPref)
                    except Exception:
                        # if eval() failed, show warning dialog and return
                        try:
                            pLabel = _localized[prefName]
                            sLabel = _localized[sectionName]
                        except Exception:
                            pLabel = prefName
                            sLabel = sectionName
                        txt = _translate(
                            'Invalid value in "%(pref)s" ("%(section)s" Tab)')
                        msg = txt % {'pref': pLabel, 'section': sLabel}
                        title = _translate('Error')
                        warnDlg = dialogs.MessageDialog(parent=self,
                                                        message=msg,
                                                        type='Info',
                                                        title=title)
                        warnDlg.ShowModal()
                        return
                    if type(newVal) != list:
                        self.prefsCfg[sectionName][prefName] = [newVal]
                    else:
                        self.prefsCfg[sectionName][prefName] = newVal
                elif self.prefsSpec[sectionName][prefName].startswith('option'):
                    vals = self.prefsSpec[sectionName][prefName].replace(
                        "option(", "").replace("'", "")
                    # item -1 is 'default=x' from spec
                    options = vals.replace(", ", ",").split(',')[:-1]
                    self.prefsCfg[sectionName][prefName] = options[thisPref]

        self.app.prefs.saveUserPrefs()  # includes a validation
        # maybe then go back and set GUI from prefs again, because validation
        # may have changed vals?
        # > sure, why not? - mdc
        self.populatePrefs()

        # after validation, update the UI
        self.app.theme = self.app.theme
        self.updateCoderUI()

    def updateCoderUI(self):
        """Update the Coder UI (eg. fonts, themes, etc.) from prefs."""
        # start applying prefs to take effect
        coder = self.app.coder
        if coder is not None:
            # apply settings over document pages
            for ii in range(coder.notebook.GetPageCount()):
                doc = coder.notebook.GetPage(ii)
                doc.theme = prefs.app['theme']
            for ii in range(coder.shelf.GetPageCount()):
                doc = coder.shelf.GetPage(ii)
                doc.theme = prefs.app['theme']

    def OnApplyClicked(self, event):
        """Apply button clicked, this makes changes to the UI without leaving
        the preference dialog. This can be used to see the effects of setting
        changes before closing the dialog.

        """
        self.applyPrefs()  # saves the preferences
        event.Skip()

    def OnCancelClicked(self, event):
        event.Skip()

    def OnHelpClicked(self, event):
        self.app.followLink(url=self.app.urls["prefs"])
        event.Skip()

    def OnOKClicked(self, event):
        """Called when OK is clicked. This closes the dialog after applying the
        settings.
        """
        self.applyPrefs()
        event.Skip()


if __name__ == '__main__':
    from psychopy import preferences
    if parse_version(wx.__version__) < parse_version('2.9'):
        app = wx.PySimpleApp()
    else:
        app = wx.App(False)
    # don't do this normally - use the existing psychopy.prefs instance
    app.prefs = preferences.Preferences()
    dlg = PreferencesDlg(app)
    dlg.ShowModal()
