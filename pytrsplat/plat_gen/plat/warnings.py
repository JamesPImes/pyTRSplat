"""Custom warnings for situations encountered before or during platting."""

__all__ = [
    'UndefinedLotWarning',
    'UnplattableWarning',
]

import pytrs


class UndefinedLotWarning(UserWarning):
    """
    A ``pytrs.Tract`` has one or more lots that have not been defined,
    so at least some of its lands cannot be shown on the plat.
    """

    @classmethod
    def from_tract(cls, tract: pytrs.Tract):
        undef_lots = []
        if hasattr(tract, 'undefined_lots'):
            undef_lots = tract.undefined_lots
        message = (
            "Undefined lots that could not be shown on the plat: "
            f"<{tract.trs}: {', '.join(undef_lots)}>"
        )
        return cls(message)


class UnplattableWarning(UserWarning):
    """
    A ``pytrs.Tract`` is completely unplattable, for any of the
    following reasons:

    * It has no identifiable lots or aliquots.
    * It has lots, but none of them are defined; and it has no
      identifiable aliquots.
    * Its Twp/Rge are undefined or otherwise erroneous.
    """

    _main_message = "Cannot add tract to plat"

    @classmethod
    def _construct(cls, tract: pytrs.Tract, submessage):
        return cls(f"{cls._main_message} ({submessage}) <{tract.quick_desc_short()}>")

    @classmethod
    def no_lots_qqs(cls, tract: pytrs.Tract):
        submessage = 'no lots or aliquots could be identified'
        return cls._construct(tract, submessage)

    @classmethod
    def only_undefined_lots(cls, tract: pytrs.Tract):
        submessage = 'all of its lots are undefined, and it has no identified aliquots'
        return cls._construct(tract, submessage)

    @classmethod
    def unclear_twprge(cls, tract: pytrs.Tract):
        submessage = 'undefined or otherwise erroneous Twp/Rge'
        return cls._construct(tract, submessage)
