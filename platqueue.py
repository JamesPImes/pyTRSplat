# Copyright (c) 2020, James P. Imes. All rights reserved.

"""Objects for queuing 'plattable' objects."""

from grid import SectionGrid, TownshipGrid, filter_tracts_by_twprge
from pyTRS.pyTRS import PLSSDesc, Tract

class PlatQueue(list):
    """A list of objects that can be incorporated into / projected onto
    a Plat object (i.e. 'plattable'). The PlatQueue object also contains
    an attribute `.tracts`, which is a SEPARATE list of the tracts
    associated with the queued plattable objects.
    These object types are plattable (i.e. can be added to a PlatQueue):
            SectionGrid, TownshipGrid, Tract"""

    # These types can be platted on a (single) Plat:
    SINGLE_PLATTABLES = (SectionGrid, TownshipGrid, Tract)

    def __init__(self, *queue_items):
        super().__init__()
        self.tracts = []
        for item in queue_items:
            if isinstance(item, (tuple, list)):
                if len(item) == 0:
                    continue
                elif len(item) == 1:
                    self.queue(item[0])
                else:
                    self.queue(item[0], item[1])

    def queue(self, plattable, tracts=None):
        """Add a 'plattable' object to the queue, and optionally add
        any corresponding tracts to the `.tracts` list as well. May
        queue ONLY a single plattable at a time, but any number of Tract
        objects may be be added to the `.tracts` attribute via the
        `tracts=` kwarg.
        (Passing an object in tracts does NOT add it to the queue!)"""

        # Make sure that `tracts` is a list.
        if tracts is None:
            tracts = []
        elif isinstance(tracts, Tract):
            # If tracts was fed as a single Tract object, put it in a list.
            tracts = [tracts]

        # If attempting to queue another PlatQueue object, we'll absorb
        # it instead.
        if isinstance(plattable, PlatQueue):
            self.absorb(plattable, tracts=tracts)
            return

        # We'll disallow PLSSDesc objects before ruling out others,
        # because they ARE allowed in MultiPlatQueue objects, so we
        # point the user in that direction.
        if isinstance(plattable, PLSSDesc):
            raise TypeError(
                'Attempted to add unplattable object to queue; PLSSDesc'
                'objects may be queued in MultiPlatQueue objects, but '
                'not PlatQueue objects.')

        # We'll disallow object types that are not in PLATTABLES.
        if not isinstance(plattable, PlatQueue.SINGLE_PLATTABLES):
            raise TypeError(f'Attempted to add unplattable object to queue; '
                            f'type: {type(plattable)}')

        # We'll also make sure that `tracts` contains only Tract objects.
        for item in tracts:
            if not isinstance(item, Tract):
                raise TypeError(f'Attempted to add non-Tract object to '
                                f'`.tracts` list; type: {type(item)}')

        # A Tract object is both plattable, and its description gets
        # (optionally) written at the bottom of the page, so if a Tract
        # was added to this queue, we check to see if it was ALSO added
        # in the `tracts` list. If it was not, we add it now.
        if isinstance(plattable, Tract):
            if not plattable in tracts:
                tracts.append(plattable)

        # The plattable itself gets added to the PlatQueue (a list)...
        self.append(plattable)

        # ...And the corresponding tracts get added to a dict, keyed by
        # the tract object.
        self.tracts.extend(tracts)

    def absorb(self, pqObj, tracts=None):
        """Absorb a PlatQueue object into this one. The kwarg `tracts=`
        should not be used directly -- it will only be used when this is
        called via `.queue()`.
        NOTE: Does not destroy the absorbed PlatQueue."""
        if tracts is None:
            tracts = []
        self.extend(pqObj)
        self.tracts.extend(pqObj.tracts)
        self.tracts.extend(tracts)


class MultiPlatQueue(dict):
    """A dict keyed by T&R (in the format of '000x000y' or fewer digits)
    of objects to use to generate a MultiPlat object. Each value is a
    PlatQueue object, which in turn is a list of objects that can be
    incorporated into / projected onto a Plat object (i.e. 'plattable').
    These object types can be added to a PlatQueue:
            SectionGrid, TownshipGrid, Tract, PLSSDesc"""

    # These types can be platted on a (single) Plat:
    MULTI_PLATTABLES = (SectionGrid, TownshipGrid, Tract, PLSSDesc)

    def __init__(self):
        super().__init__()

    def queue(self, plattable, twprge='', tracts=None):
        """Add the `plattable` object to the PlatQueue for the
        respective `twprge` (in the format '000z000y'). If no PlatQueue
        yet exists for that twprge (i.e. if that twprge is not yet a key
        in this MultiPlatQueue object), a PQ object will be created.

        NOTE: If a PLSSDesc object is fed in, `twprge` and `tracts` are
        ignored, but rather are deduced automatically (because there can
        be more than one T&R from a single PLSSDesc object).

        NOTE ALSO: If a Tract object is passed as `plattable`, then
        `twprge` is optional (as long as the Tract object has a
        specified `.twp` and `.rge`), and `tracts` is always optional.
        However, the Tract object's `.twp` and `.rge` will NOT overrule
        a kwarg-specified `twprge=` (if any)."""

        def breakout_plssdesc(descObj):
            """PLSSDesc objects must be handled specially, because they
            can generate multiple T&R's (i.e. multiple dict keys)."""
            twp_to_tract = filter_tracts_by_twprge(descObj)
            for twprge, tract_list in twp_to_tract.items():
                self.setdefault(twprge, PlatQueue())
                for tract in tract_list:
                    self[twprge].queue(tract)
            return

        def handle_tract(tractObj, twprge=None, tracts=None):
            """Tract object can be handled specially too, because it can
            also have T&R specified internally. Return the original
            plattable -- but also the twprge and tracts, if they were
            not specified."""

            # If twprge was not specified for this object, pull it from
            # the Tract object itself.
            if twprge in ['', None]:
                twp, rge = tractObj.twp.lower(), tractObj.rge.lower()
                twprge = twp+rge
                # TODO: Handle TRerr twp/rge.
            else:
                twprge = twprge.lower()

            # Ensure this Tract object has been added to the tract list.
            confirmed_tracts = []
            if tracts is not None:
                confirmed_tracts.extend(tracts)
            if tractObj not in confirmed_tracts:
                confirmed_tracts.append(tractObj)

            return tractObj, twprge, confirmed_tracts

        if not isinstance(plattable, MultiPlatQueue.MULTI_PLATTABLES):
            raise TypeError(f"Cannot add type to MultiPlatQueue: "
                            f"{type(plattable)}")
            return

        # Handle PLSSDesc object, if it is one.
        if isinstance(plattable, PLSSDesc):
            breakout_plssdesc(plattable)
            return

        # Handle Tract object, if it is one.
        if isinstance(plattable, Tract):
            plattable, twprge, tracts = handle_tract(plattable, twprge, tracts)

        if len(twprge) == 0:
            raise ValueError(
                "To queue up objects other than PLSSDesc or Tract, "
                "'twprge' must be specified as a non-empty string, to "
                "serve as dict key.")

        twprge = twprge.lower()
        # If the twprge does not already exist as a key, create a
        # PlatQueue object for that T&R, and add it to the dict now.
        self.setdefault(twprge, PlatQueue())
        self[twprge].queue(plattable, tracts)

    def absorb(self, mpq):
        """Absorb a MultiPlatQueue object into this one."""
        for twprge, pq in mpq.items():
            # If a PQ for this T&R does not yet exist, we'll create one now.
            self.setdefault(twprge, PlatQueue())

            # And instruct our new PQ to absorb the PQ from our subordinate MPQ
            self[twprge].absorb(pq)

    def queue_text(self, text, config=None):
        """Parse the text of a PLSS land description (optionally using
        `config=` parameters -- see pyTRS docs), and add the resulting
        PLSSDesc object to this MultiPlatQueue."""
        descObj = PLSSDesc(text, config=config, initParseQQ=True)
        self.queue(descObj)