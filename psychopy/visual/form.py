#!/usr/bin/env python
# -*- coding: utf-8 -*-


# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).
from __future__ import division
from collections import deque
import psychopy
from .text import TextStim
from psychopy.data.utils import importConditions
from psychopy.visual.basevisual import (BaseVisualStim,
                                        ContainerMixin,
                                        ColorMixin)
from psychopy import logging
from random import shuffle

from psychopy.constants import PY3

__author__ = 'Jon Peirce, David Bridges, Anthony Haffey'

_REQUIRED = -12349872349873  # an unlikely int

# a dict of known fields with their default vals
_knownFields = {
    'index': None,  # optional field to index into the rows
    'itemText': _REQUIRED,  # (question used until 2020.2)
    'itemColor': 'white',
    'itemWidth': 0.8,  # fraction of the form
    'type': _REQUIRED,  # type of response box (see below)
    'options': ('Yes', 'No'),  # for choice box
    'ticks': (1, 2, 3, 4, 5, 6, 7), 'tickLabels': None,
    # for rating/slider
    'responseWidth': 0.8,  # fraction of the form
    'responseColor': 'white',
    'layout': 'horiz',  # can be vert or horiz
}
_knownRespTypes = {
    'heading', 'description',  # no responses
    'rating', 'slider',  # slider is continuous
    'free text',
    'choice', 'radio'  # synonyms (radio was used until v2020.2)
}
_synonyms = {
    'itemText': 'questionText',
    'choice': 'radio',
    'free text': 'textBox'
}

class Form(BaseVisualStim, ContainerMixin, ColorMixin):
    """A class to add Forms to a `psycopy.visual.Window`

    The Form allows Psychopy to be used as a questionnaire tool, where
    participants can be presented with a series of questions requiring responses.
    Form items, defined as questions and response pairs, are presented
    simultaneously onscreen with a scrollable viewing window.

    Example
    -------
    survey = Form(win, items=[{}], size=(1.0, 0.7), pos=(0.0, 0.0))

    Parameters
    ----------
    win : psychopy.visual.Window
        The window object to present the form.
    items : List of dicts or csv or xlsx file
        a list of dicts or csv file should have the following key, value pairs / column headers:
                 "index": The item index as a number
                 "itemText": item question string,
                 "itemWidth": fraction of the form width 0:1
                 "type": type of rating e.g., 'radio', 'rating', 'slider'
                 "responseWidth": fraction of the form width 0:1,
                 "options": list of tick labels for options,
                 "layout": Response object layout e.g., 'horiz' or 'vert'
    textHeight : float
        Text height.
    size : tuple, list
        Size of form on screen.
    pos : tuple, list
        Position of form on screen.
    itemPadding : float
        Space or padding between form items.
    units : str
        units for stimuli - Currently, Form class only operates with 'height' units.
    randomize : bool
        Randomize order of Form elements
    """

    def __init__(self,
                 win,
                 name='default',
                 items=None,
                 textHeight=.02,
                 size=(.5, .5),
                 pos=(0, 0),
                 itemPadding=0.05,
                 units='height',
                 randomize=False,
                 autoLog=True,
                 ):

        super(Form, self).__init__(win, units, autoLog=False)
        self.win = win
        self.autoLog = autoLog
        self.name = name
        self.randomize = randomize
        self.items = self.importItems(items)
        self.size = size
        self.pos = pos
        self.itemPadding = itemPadding
        self.scrollSpeed = self.setScrollSpeed(self.items, 4)
        self.units = units

        self.textHeight = textHeight
        self._scrollBarSize = (0.016, size[1])
        self._baseYpositions = []
        self.leftEdge = None
        self.rightEdge = None
        self.topEdge = None
        self.virtualHeight = 0  # Virtual height determines pos from boundary box
        self._decorations = []
        # Check units - only works with height units for now
        if self.win.units != 'height':
            logging.warning(
                "Form currently only formats correctly using height units. "
                "Please change the units in Experiment Settings to 'height'")

        self.complete = False

        # Create layout of form
        self._doLayout()

        if self.autoLog:
            logging.exp("Created {} = {}".format(self.name, repr(self)))

    def __repr__(self, complete=False):
        return self.__str__(complete=complete)  # from MinimalStim

    def importItems(self, items):
        """Import items from csv or excel sheet and convert to list of dicts.
        Will also accept a list of dicts.

        Note, for csv and excel files, 'options' must contain comma separated values,
        e.g., one, two, three. No parenthesis, or quotation marks required.

        Parameters
        ----------
        items :  Excel or CSV file, list of dicts
            Items used to populate the Form

        Returns
        -------
        List of dicts
            A list of dicts, where each list entry is a dict containing all fields for a single Form item
        """
        def _checkSynonyms(items, fieldNames):
            """Checks for updated names for fields (i.e. synonyms)"""
            replacedFields = set()
            for field in _synonyms:
                synonym = _synonyms[field]
                for item in items:
                    if synonym in item:
                        # convert to new name
                        item[field] = item[synonym]
                        del item[synonym]
                        replacedFields.add(field)
            for field in replacedFields:
                fieldNames.add(field)
                fieldNames.remove(_synonyms[field])
                logging.warning("Form {} included field no longer used {}. "
                                "Replacing with new name '{}'"
                                .format(self.name, _synonyms[field], field))

        def _checkRequiredFields(fieldNames):
            """Checks for required headings (do this after checking synonyms)"""
            for hdr in _knownFields:
                # is it required and/or present?
                if _knownFields[hdr] == _REQUIRED and hdr not in fieldNames:
                    raise ValueError("Missing header ({}) in Form ({}). "
                                     "Headers found were: {}"
                                     .format(hdr, self.name, fieldNames))


        def _checkTypes(types):
            """A nested function for testing the number of options given

            Raises ValueError if n Options not > 1
            """
            itemDiff = set([types]) - set(_knownRespTypes)

            if len(itemDiff) > 0:
                msg = ("In Forms, {} is not allowed. You can only use types {}."
                       " Please amend your item types in your item list"
                       .format(itemDiff, _knownRespTypes))
                if self.autoLog:
                    logging.error(msg)
                raise ValueError(msg)

        def _addDefaultItems(items):
            """
            Adds default items when missing. Works in-place.

            Parameters
            ----------
            items : List of dicts
            headers : List of column headers for each item
            """
            def isPresent(d, field):
                # check if the field is there and not empty on this row
                return (field in d and d[field] not in [None, ''])

            missingHeaders = []
            defaultValues = _knownFields
            for index, item in enumerate(items):
                defaultValues['index'] = index
                for header in defaultValues:
                    # if header is missing of val is None or ''
                    if not isPresent(item, header):
                        oldHeader = header.replace('item', 'question')
                        if isPresent(item, oldHeader):
                            item[header] = item[oldHeader]
                            logging.warning(
                                "{} is a deprecated heading for Forms. "
                                "Use {} instead"
                                .format(oldHeader, header)
                            )
                            continue

                        item[header] = defaultValues[header]
                        missingHeaders.append(header)

            msg = "Using default values for the following headers: {}".format(
                missingHeaders)
            if self.autoLog:
                logging.info(msg)

        if self.autoLog:
            logging.info("Importing items...")

        if not isinstance(items, list):
            # items is a conditions file
            items, fieldNames = importConditions(items, returnFieldNames=True)
        else:  # we already have a list so lets find the fieldnames
            fieldNames = set()
            for item in items:
                fieldNames = fieldNames.union(item)

        _checkSynonyms(items, fieldNames)
        _checkRequiredFields(fieldNames)
        # Add default values if entries missing
        _addDefaultItems(items)

        # Convert options to list of strings
        for idx, item in enumerate(items):
            if PY3:
                if isinstance(item['options'], str):
                    items[idx]['options'] = item['options'].split(',')
            else:  # Python2
                if isinstance(item['options'], basestring):
                    items[idx]['options'] = item['options'].split(',')

        # Check types
        [_checkTypes(item['type']) for item in items]
        # Check N options > 1
        # Randomise items if requested
        if self.randomize:
            shuffle(items)
        return items

    def setScrollSpeed(self, items, multiplier=2):
        """Set scroll speed of Form. Higher multiplier gives smoother, but
        slower scroll.

        Parameters
        ----------
        items : list of dicts
            Items used to populate the form
        multiplier : int (default=2)
            Number used to calculate scroll speed

        Returns
        -------
        int
            Scroll speed, calculated using N items by multiplier
        """
        return len(items) * multiplier

    def _getItemRenderedWidth(self, size):
        """Returns text width for item text based on itemWidth and Form width.

        Parameters
        ----------
        size : float, int
            The question width

        Returns
        -------
        float
            Wrap width for question text
        """
        return size * self.size[0] - (self.itemPadding * 2)

    def _responseTextWrap(self, item):
        """
        Returns width for each response label text based on responseWidth
        and N responses given for item.

        Parameters
        ----------
        item : dict
            The dict entry for a single item

        Returns
        -------
        float
            Wrap width for response label text
        """
        return (item['responseWidth'] * self.size[0]) / (len(item['options']))

    def _setQuestion(self, item):
        """Creates TextStim object containing question

        Parameters
        ----------
        item : dict
            The dict entry for a single item

        Returns
        -------
        psychopy.visual.text.TextStim
            The textstim object with the question string
        questionHeight
            The height of the question bounding box as type float
        questionWidth
            The width of the question bounding box as type float
        """
        if self.autoLog:
            logging.exp(
                    u"Question text: {}".format(item['itemText']))

        if item['type'] == 'heading':
            letterScale = 1.5
            bold = True
        else:
            letterScale = 1.0
            bold = False
        w = self._getItemRenderedWidth(item['itemWidth'])
        question = psychopy.visual.TextBox2(
                self.win,
                text=item['itemText'],
                units=self.units,
                letterHeight=self.textHeight * letterScale,
                anchor='center-left',
                size=[w, 0.05],
                autoLog=False,
                color=item['itemColor'],
                borderWidth=1,
                editable=False,
                bold=bold,
                font='Arial')

        questionHeight = self._getQuestionHeight(question)
        questionWidth = self._getQuestionWidth(question)

        # Position text relative to boundaries defined according to pos and size
        question.pos = self._getQuestionPos(questionHeight)

        # Add question objects to Form element dict
        item['itemCtrl'] = question

        return question, float(questionHeight), float(questionWidth)

    def _setResponse(self, item, question):
        """Makes calls to methods which make Slider or TextBox response objects
        for Form

        Parameters
        ----------
        item : dict
            The dict entry for a single item
        question : TextStim
            The question text object

        Returns
        -------
        psychopy.visual.slider.Slider
            The Slider object for response
        psychopy.visual.TextBox
            The TextBox object for response
        respHeight
            The height of the response object as type float
        """
        if self.autoLog:
            logging.exp("Response type: {}".format(item['type']))
            logging.exp("Response layout: {}".format(item['layout']))
            logging.exp(u"Response options: {}".format(item['options']))

        # Create position of response object
        pos = self._getResponsePos(item, question)

        if item['type'].lower() == 'free text':
            respCtrl, respHeight = self._makeTextBox(item, pos)
        elif item['type'].lower() in ['heading', 'description']:
            respCtrl, respHeight = None, self.textHeight
        elif item['type'].lower() in ['rating', 'slider', 'choice', 'radio']:
            respCtrl, respHeight = self._makeSlider(item, pos)

        item['responseCtrl'] = respCtrl
        return respCtrl, float(respHeight)

    def _getQuestionPos(self, questionHeight):
        """Sets initial position of question text object

        Parameters
        ----------
        questionHeight : float
            The height of the question bounding box

        Returns
        -------
        Tuple
            The position of the text object
        """
        pos = (self.leftEdge + (self.itemPadding / 2),
               self.topEdge
               + self.virtualHeight
               - questionHeight / 2 - self.itemPadding)
        return pos

    def _getResponsePos(self, item, question):
        """Sets initial position of question object

        Parameters
        ----------
        question : TextStim
            The question text object
        item : dict
            The dict entry for a single item

        Returns
        -------
        Tuple
            The position of the response object
        """
        pos = (self.rightEdge
               - ((item['responseWidth'] * self.size[0]) / 2)
               - self._scrollBarSize[0]
               - self.itemPadding
               * self.size[0],
               question.pos[1])
        return pos

    def _makeSlider(self, item, pos):
        """Creates Slider object for Form class

        Parameters
        ----------
        item : dict
            The dict entry for a single item
        pos : tuple
            position of response object

        Returns
        -------
        psychopy.visual.slider.Slider
            The Slider object for response
        respHeight
            The height of the response object as type float
        """
        # Slider dict

        sliderType = {'slider': {'ticks': range(0, len(item['options'])),
                                 'style': 'slider', 'granularity': 0},
                      'rating': {'ticks': range(0, len(item['options'])),
                                 'style': 'rating', 'granularity': 1},
                      'choice': {'ticks': None,
                                 'style': 'radio', 'granularity': 1}}
        sliderType['radio'] = sliderType['choice']  # synonyms

        # Get height of response object
        respHeight = self._getSliderHeight(item)

        # Set radio button layout
        if item['layout'] == 'horiz':
            respSize = ((item['responseWidth'])
                        * self.size[0]
                        - self._scrollBarSize[0]
                        - self.itemPadding,
                        0.03)
        elif item['layout'] == 'vert':
            respSize = (0.03, respHeight)
            item['options'].reverse()

        # Create Slider
        resp = psychopy.visual.Slider(
                self.win,
                pos=pos, size=respSize,
                ticks=sliderType[item['type'].lower()]['ticks'],
                labels=[i.strip(' ') for i in item['options']],
                units=self.units,
                labelHeight=self.textHeight,
                labelWrapWidth=self._responseTextWrap(item),
                granularity=sliderType[item['type'].lower()]['granularity'],
                flip=True,
                style=sliderType[item['type'].lower()]['style'],
                autoLog=False,
                color=item['responseColor'])

        return resp, respHeight

    def _makeTextBox(self, item, pos):
        """Creates TextBox object for Form class

        NOTE: The TextBox 2 in work in progress, and has not been added to Form class yet.
        Parameters
        ----------
        item : dict
            The dict entry for a single item
        pos : tuple
            position of response object

        Returns
        -------
        psychopy.visual.TextBox
            The TextBox object for response
        respHeight
            The height of the response object as type float
        """
        resp = psychopy.visual.TextBox2(
                self.win,
                text='',
                pos=pos,
                size=(item['responseWidth'], .25),
                letterHeight=self.textHeight,
                units=self.units,
                color='white',
                font='Arial',
                editable=True,
                borderColor='orange',
                fillColor='lightgray',
        )

        respHeight = resp.size[1] / 2
        return resp, respHeight

    def _getQuestionHeight(self, question=None):
        """Takes TextStim and calculates height of bounding box relative to height units of win

        Parameters
        ----------
        question : TextStim
            The question text object

        Returns
        -------
        float
            The height of the question bounding box
        """
        return question.box.size[1] / float(self.win.size[1])

    def _getQuestionWidth(self, question=None):
        """Takes TextStim and calculates width of bounding box relative to height units of win

        Parameters
        ----------
        question : TextStim
            The question text object

        Returns
        -------
        float
            The width of the question bounding box
        """
        return question.box.size[1] / float(self.win.size[1])

    def _getSliderHeight(self, item):
        """Takes response items and calculates height of response object
        based on the size of the textstim bounding box

        Parameters
        ----------
        item : dict
            The dict entry for a single item

        Returns
        -------
        float
            The height of the response object
        """
        longest = max(item['options'], key=len)  # Get longest response item
        LongestIndex = item['options'].index(longest)  # index longest item
        tempText = TextStim(self.win,
                            item['options'][LongestIndex],
                            height=self.textHeight,
                            wrapWidth=self._responseTextWrap(item))
        size = tempText.boundingBox[1]
        del (tempText)

        # set response height from layout
        if item['layout'] == 'vert':
            respHeight = len(item['options']) * size
        elif item['layout'] == 'horiz':
            respHeight = size

        # return size converted to height units
        return respHeight / self.win.size[1] + self.itemPadding

    def _setScrollBar(self):
        """Creates Slider object for scrollbar

        Returns
        -------
        psychopy.visual.slider.Slider
            The Slider object for scroll bar
        """
        return psychopy.visual.Slider(win=self.win,
                                      size=self._scrollBarSize,
                                      ticks=[0, 1],
                                      style='slider',
                                      pos=(self.rightEdge - .008, self.pos[1]),
                                      autoLog=False)

    def _setBorder(self):
        """Creates border using Rect

        Returns
        -------
        psychopy.visual.Rect
            The border for the survey
        """
        return psychopy.visual.Rect(win=self.win,
                                    units=self.units,
                                    pos=self.pos,
                                    width=self.size[0],
                                    height=self.size[1],
                                    autoLog=False)

    def _setAperture(self):
        """Blocks text beyond border using Aperture

        Returns
        -------
        psychopy.visual.Aperture
            The aperture setting viewable area for forms
        """
        aperture = psychopy.visual.Aperture(win=self.win,
                                            name='aperture',
                                            units=self.units,
                                            shape='square',
                                            size=self.size,
                                            pos=(0, 0),
                                            autoLog=False)
        aperture.disable()  # Disable on creation. Only enable on draw.
        return aperture

    def _getScrollOffset(self):
        """Calculate offset position of items in relation to markerPos

        Returns
        -------
        float
            Offset position of items proportionate to scroll bar
        """
        sizeOffset = (1 - self.scrollbar.markerPos) * (
                    self.size[1] - self.itemPadding)
        maxItemPos = min(self._baseYpositions)
        if maxItemPos > -self.size[1]:
            return 0
        return (maxItemPos - (
                    self.scrollbar.markerPos * maxItemPos) + sizeOffset)

    def _setBaseYPosition(self, respHeight, questionHeight, layout):
        """Sets the item position based on question vs. response height

        Parameters
        ----------
        respHeight : float
            The height of a response object
        questionHeight : float
            The height of a question text object
        layout : string
            The layout of the Form item - vert or horiz
        """
        # Append item height
        self._baseYpositions.append(self.virtualHeight
                                    - max(respHeight,
                                          questionHeight)  # Positionining based on larger of the two
                                    + (respHeight / 2) * (
                                                layout == 'vert')  # aligns to center
                                    - self.itemPadding)  # Padding for unaccounted marker size in slider height
        # update height ready for next item/row
        self.virtualHeight -= (max(respHeight, questionHeight)
                               + self.itemPadding)

    def _doLayout(self):
        """Define layout of form"""
        # Define boundaries of form
        if self.autoLog:
            logging.info("Setting layout of Form: {}.".format(self.name))

        self.leftEdge = self.pos[0] - self.size[0] / 2.0
        self.rightEdge = self.pos[0] + self.size[0] / 2.0
        self.topEdge = self.pos[1] + self.size[1] / 2.0

        # For each question, create textstim and rating scale
        for item in self.items:
            # set up the question object
            question, questionHeight, questionWidth = self._setQuestion(item)
            # set up the response object
            response, respHeight, = self._setResponse(item, question)
            # Calculate position of item based on larger questionHeight vs respHeight.
            self._setBaseYPosition(respHeight, questionHeight, item['layout'])

        # position a slider on right-hand edge
        self.scrollbar = self._setScrollBar()
        self.scrollbar.markerPos = 1  # Set scrollbar to start position
        self.border = self._setBorder()
        self.aperture = self._setAperture()
        self._setDecorations()

        if self.autoLog:
            logging.info("Layout set for Form: {}.".format(self.name))

    def _setDecorations(self):
        """Sets Form decorations i.e., Border and scrollbar"""
        # add scrollbar if it's needed
        self._decorations = [self.border]
        fractionVisible = self.size[1] / (-self.virtualHeight)
        if fractionVisible < 1.0:
            self._decorations.append(self.scrollbar)

    def _inRange(self, item):
        """Check whether item position falls within border area

        Parameters
        ----------
        item : TextStim, Slider object
            TextStim or Slider item from survey

        Returns
        -------
        bool
            Returns True if item position falls within border area
        """
        upperRange = self.size[1]
        lowerRange = -self.size[1]
        return (item.pos[1] < upperRange and item.pos[1] > lowerRange)

    def _drawDecorations(self):
        """Draw decorations on form."""
        [decoration.draw() for decoration in self._decorations]

    def _drawCtrls(self):
        """Draw elements on form within border range.

        Parameters
        ----------
        items : List
            List of TextStim or Slider item from survey
        """
        for idx, item in enumerate(self.items):
            for element in [item['itemCtrl'], item['responseCtrl']]:
                if element is None:  # e.g. because this has no resp obj
                    continue

                element.pos = (element.pos[0], self.size[1] / 2
                               + self._baseYpositions[idx]
                               - self._getScrollOffset())
                if self._inRange(element):
                    element.draw()

    def draw(self):
        """Draw all form elements"""
        # Check mouse wheel
        self.scrollbar.markerPos += self.scrollbar.mouse.getWheelRel()[
                                        1] / self.scrollSpeed
        # enable aperture
        self.aperture.enable()
        # draw the box and scrollbar
        self._drawDecorations()
        # Draw question and response objects
        self._drawCtrls()
        # disable aperture
        self.aperture.disable()

    def getData(self):
        """Extracts form questions, response ratings and response times from Form items

        Returns
        -------
        dict
            A dictionary storing lists of questions, response ratings and response times
        """
        formData = {'itemIndex': deque([]), 'questions': deque([]),
                    'ratings': deque([]), 'rt': deque([])}
        nIncomplete = 0
        nIncompleteRequired = 0
        for thisItem in self.items:
            if 'responseCtrl' not in thisItem:
                continue  # maybe a heading or similar
            responseCtrl = thisItem['responseCtrl']
            # get response if available
            if hasattr(responseCtrl, 'getRating'):
                thisItem['response'] = responseCtrl.getRating()
            else:
                thisItem['response'] = responseCtrl.text
            if thisItem['response'] in [None,'']:
                # todo : handle required items here (e.g. ending with * ?)
                nIncomplete += 1
            # get RT if available
            if hasattr(responseCtrl, 'getRT'):
                thisItem['rt'] = responseCtrl.getRT()
            else:
                thisItem['rt'] = None
        self.complete = (nIncomplete==0)
        return self.items

    def formComplete(self):
        """Checks all Form items for a response

        Returns
        -------
        bool
            True if all items contain a response, False otherwise.
        """
        self.getData()
        return self.complete
