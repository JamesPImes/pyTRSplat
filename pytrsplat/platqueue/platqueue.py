# Copyright (c) 2020, James P. Imes. All rights reserved.

"""
Streamlined queues of 'plattable' objects.
"""

from pytrsplat.grid import SectionGrid, TownshipGrid
from pytrsplat.utils import filter_tracts_by_twprge
import pytrs


class PlatQueue(list):
    """
    A list of objects that can be incorporated into / projected onto a
    Plat object (i.e. 'plattable'). The PlatQueue object also contains
    an attribute `.tracts`, which is a SEPARATE list of the pytrs.Tract
    objects associated with the queued plattable objects (i.e. it is a
    list of Tract objects whose text will eventually be written at the
    bottom of the Plat, if the Plat is configured to do so).

    These object types are plattable (i.e. can be added to a PlatQueue):
        -- pytrsplat.SectionGrid
        -- pytrsplat.TownshipGrid
        -- pytrs.Tract
    Add objects with the `.queue_add()` method.

    Or absorb another PlatQueue object with `.absorb()`.
    """

    # These types can be platted on a (single) Plat:
    SINGLE_PLATTABLES = (SectionGrid, TownshipGrid, pytrs.Tract)

    def __init__(self):
        """
        Do not pass any arguments at init. Use the `.queue_add()`
        and/or `.absorb()` methods after init.
        """
        super().__init__()
        self.tracts = []

    def queue_add(self, plattable, tracts=None):
        """
        Queue up an object for platting -- i.e. add the object to this
        queue, and optionally add any corresponding tracts to the
        `.tracts` list as well.

        NOTE: A PlatQueue can contain any number of plattable objects,
        but only one may be added via this method at a time. However,
        the list passed as `tracts=` (if any) can contain any number of
        pytrs.Tract objects (which get appended to the `.tracts`
        attribute of this PlatQueue).

        IMPORTANT: Passing an object in `tracts` does NOT add it to the
        queue to be platted -- only to the tracts whose text will be
        written at the bottom of the plat(s), if so configured.

        :param plattable: The object to be added to the queue. (Must be
        a type acceptable to PlatQueue -- see docs for those objects.)
        :param tracts: A list of pytrs.Tract objects whose text should
        eventually be written at the bottom of the Plat (assuming the
        Plat is configured in settings to write Tract text).
        NOTE: Objects added to `tracts` do NOT get drawn on the plat --
        only written at the bottom. But pytrs.Tract objects passed here
        as arg `plattable` are automatically added to `tracts`.
        """

        # Make sure that `tracts` is a list.
        if tracts is None:
            tracts = []
        elif isinstance(tracts, pytrs.Tract):
            # If tracts was fed as a single Tract object, put it in a list.
            tracts = [tracts]

        # If attempting to add another PlatQueue object, we'll absorb
        # it instead.
        if isinstance(plattable, PlatQueue):
            self.absorb(plattable, tracts=tracts)
            return

        # We'll disallow PLSSDesc objects before ruling out others,
        # because they ARE allowed in MultiPlatQueue objects, so we
        # point the user in that direction.
        if isinstance(plattable, pytrs.PLSSDesc):
            raise TypeError(
                'Attempted to add unplattable object to queue; pytrs.PLSSDesc '
                'objects may be queued in MultiPlatQueue objects, but '
                'not PlatQueue objects.')

        # We'll disallow object types that are not in PLATTABLES.
        if not isinstance(plattable, PlatQueue.SINGLE_PLATTABLES):
            raise TypeError(f'Attempted to add unplattable object to queue; '
                            f'type: {type(plattable)}')

        # We'll also make sure that `tracts` contains only Tract objects.
        for item in tracts:
            if not isinstance(item, pytrs.Tract):
                raise TypeError(
                    f'Attempted to add object other than  pytrs.Tract to '
                    f'`tracts` list; type: {type(item)}')

        # A Tract object is both plattable, and its description gets
        # (optionally) written at the bottom of the page, so if a Tract
        # was added to this queue, we check to see if it was ALSO added
        # in the `tracts` list. If it was not, we add it now.
        if isinstance(plattable, pytrs.Tract):
            if plattable not in tracts:
                tracts.append(plattable)

        # The plattable itself gets added to the PlatQueue (a list)...
        self.append(plattable)

        # ...And the corresponding tracts get added to a dict, keyed by
        # the tract object.
        self.tracts.extend(tracts)

    def absorb(self, pqObj, tracts=None):
        """
        Absorb a PlatQueue object into this one. The parameter `tracts=`
        should not be used directly -- it will only be used when this is
        called via `.queue_add()`.
        NOTE: Does not destroy the absorbed PlatQueue.
        """
        if tracts is None:
            tracts = []
        self.extend(pqObj)
        self.tracts.extend(pqObj.tracts)
        self.tracts.extend(tracts)


class MultiPlatQueue(dict):
    """
    A dict keyed by T&R (in the format of '000x000y' or fewer digits)
    of objects to use to generate a MultiPlat object. Each value in the
    MultiPlatQueue is a PlatQueue object, which in turn is a list of
    objects that can be incorporated into / projected onto a Plat object
    (i.e. 'plattable').

    These object types can be added to a MultiPlatQueue:
        -- pytrsplat.SectionGrid [*]
        -- pytrsplat.TownshipGrid [*]
        -- pytrsplat.PlatQueue [*]
        -- pytrs.Tract [**]
        -- pytrs.PLSSDesc [***]
        [*] Single asterisk denotes object types for which twprge must
            be specified when adding to the queue (i.e. which Twp/Rge do
            these objects belong to).
        [**] Double asterisk denotes object types for which twprge may
            optionally be specified when adding to the queue (if not
            specified, will be pulled from the object itself, as long as
            that object has appropriate `.twp` and `.rge` attributes).
        [***] Specifying twprge for pytrs.PLSSDesc objects has no effect
            (it can be specified but will be disregarded), because
            PLSSDesc objects automatically contain Twp/Rge data by
            definition, and because they can have multiple Twp/Rge.
    """

    # These types can be platted onto a MultiPlat:
    MULTI_PLATTABLES = (
        SectionGrid, TownshipGrid, pytrs.Tract, pytrs.PLSSDesc, PlatQueue)

    def __init__(self):
        """
        Do not pass any arguments at init. Use the `.queue_add()`,
        `.queue_add_text()`, and/or `.absorb()` methods after init.
        """
        super().__init__()

    def queue_add(self, plattable, twprge='', tracts=None):
        """
        Queue up an object for platting -- i.e. add that object to the
        PlatQueue object for the specified `twprge` (in the format
        '000z000y', or fewer digits). If no PlatQueue yet exists for
        that twprge (i.e. if that twprge is not yet a key in this
        MultiPlatQueue object), a PQ object will be created.

        NOTE: If a pytrs.PLSSDesc object is passed as the `plattable`,
        then `twprge` and `tracts` are ignored, but rather are deduced
        automatically (because there can be more than one T&R from a
        single PLSSDesc object).

        NOTE ALSO: If a pytrs.Tract object is passed as the `plattable`,
        then `twprge` is optional (as long as the Tract object has a
        specified `.twp` and `.rge`), and `tracts` is always optional.
        However, the Tract object's `.twp` and `.rge` will NOT overrule
        a kwarg-specified `twprge=` (if any).

        :param plattable: The object to be added to the queue. (Must be
        a type acceptable to MultiPlatQueue -- see docs for those
        objects.)
        :param twprge: A string of the Twp/Rge (e.g., '154n97w' or
        '1s8e') to which the plattable object belongs.
            ex: If queuing up a pytrs.SectionGrid object for Section 1,
                T154N-R97W, then `twprge` should be '154n97w'.
        NOTE: `twprge` is ignored when a pytrs.PLSSDesc object is passed
            as `plattable`.
        NOTE ALSO: `twprge` is optional when a pytrs.Tract object is
            passed as `plattable`, as long as the Tract object has
            appropriate `.twp` and `.rge` attributes. If `twprge=` is
            specified in this method, that will control over whatever is
            in the Tract object's `.twp` and `.rge` attributes.
        :param tracts: A list of pytrs.Tract objects whose text should
        eventually be written at the bottom of the appropriate Plat
        (assuming the MultiPlat is configured in settings to write Tract
        text).
        NOTE: Objects added to `tracts` do NOT get drawn on the plats --
        only written at the bottom. But pytrs.Tract objects passed here
        as arg `plattable` are automatically added to `tracts`.
        """

        def breakout_plssdesc(descObj):
            """
            pytrs.PLSSDesc objects MUST be handled specially, because
            they can generate multiple T&R's (i.e. multiple dict keys).
            """
            twp_to_tract = filter_tracts_by_twprge(descObj)
            for twprge, tract_list in twp_to_tract.items():
                self.setdefault(twprge, PlatQueue())
                for tract in tract_list:
                    self[twprge].queue_add(tract)
            return

        def handle_tract(tractObj, twprge=None, tracts=None):
            """
            pytrs.Tract object can be handled specially too, because it
            can also have T&R specified internally. Return the original
            plattable -- but also the twprge and tracts, if they were
            not specified.
            """

            # If twprge was not specified for this object, pull it from
            # the Tract object itself.
            if twprge in ['', None]:
                twp, rge = tractObj.twp.lower(), tractObj.rge.lower()
                twprge = twp+rge
                if twprge == '':
                    # i.e. tract.twp and tract.rge were both also ''
                    twprge = 'undef'
            else:
                twprge = twprge.lower()

            # Smooth out any variations of 'TRerrTRerr', 'TRerr_', etc.
            if 'trerr' in twprge.lower():
                twprge = 'TRerr'

            # Ensure this Tract object has been added to the tract list.
            confirmed_tracts = []
            if tracts is not None:
                confirmed_tracts.extend(tracts)
            if tractObj not in confirmed_tracts:
                confirmed_tracts.append(tractObj)

            return tractObj, twprge, confirmed_tracts

        def handle_platqueue(pq, twprge=None, tracts=None):
            """
            PlatQueue object can be handled specially too, because it
            should be absorbed, if a PQ already exists for that T&R,
            rather than added.
            """
            if twprge is None:
                raise ValueError(
                    '`twprge` must be specified when adding a PlatQueue '
                    'to a MultiPlatQueue.')
            if tracts is not None:
                pq.tracts.extend(tracts)
            self.setdefault(twprge, PlatQueue())
            self[twprge].absorb(pq)
            return

        if not isinstance(plattable, MultiPlatQueue.MULTI_PLATTABLES):
            raise TypeError(f"Cannot add type to MultiPlatQueue: "
                            f"{type(plattable)}")

        # Handle PLSSDesc object, if it is one.
        if isinstance(plattable, pytrs.PLSSDesc):
            breakout_plssdesc(plattable)
            return

        # Handle PlatQueue object, if it is one.
        if isinstance(plattable, PlatQueue):
            handle_platqueue(plattable, twprge, tracts)
            return

        # Handle Tract object, if it is one.
        if isinstance(plattable, pytrs.Tract):
            plattable, twprge, tracts = handle_tract(plattable, twprge, tracts)

        if len(twprge) == 0:
            raise ValueError(
                "To add objects other than pytrs.PLSSDesc or pytrs.Tract to "
                "queue, 'twprge' must be specified as a non-empty string, to "
                "serve as dict key.")

        twprge = twprge.lower()
        # If the twprge does not already exist as a key, create a
        # PlatQueue object for that T&R, and add it to the dict now.
        self.setdefault(twprge, PlatQueue())
        self[twprge].queue_add(plattable, tracts)

    def absorb(self, mpq):
        """
        Absorb a MultiPlatQueue object into this one.
        """
        for twprge, pq in mpq.items():
            # If a PQ for this T&R does not yet exist, we'll create one now.
            self.setdefault(twprge, PlatQueue())

            # And instruct our new PQ to absorb the PQ from our subordinate MPQ
            self[twprge].absorb(pq)

    def queue_add_text(self, text, config=None):
        """
        Parse the raw text of a PLSS land description (optionally using
        `config=` parameters -- see pytrs docs), and add the resulting
        PLSSDesc object to this MultiPlatQueue.
        """
        descObj = pytrs.PLSSDesc(text, config=config, init_parse_qq=True)
        self.queue_add(descObj)
