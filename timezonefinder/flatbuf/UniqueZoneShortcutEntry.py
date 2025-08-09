# UniqueZoneShortcutEntry
import flatbuffers


class UniqueZoneShortcutEntry:
    __slots__ = ["_tab"]

    @classmethod
    def GetRootAs(cls, buf, offset=0):
        n = flatbuffers.encode.Get(buf, offset)
        x = UniqueZoneShortcutEntry()
        x.Init(buf, n)
        return x

    @classmethod
    def GetRootAsUniqueZoneShortcutEntry(cls, buf, offset=0):
        return cls.GetRootAs(buf, offset)

    # UniqueZoneShortcutEntry
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # UniqueZoneShortcutEntry
    def HexId(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.Get(
                flatbuffers.number_types.Uint64Flags, o + self._tab.Pos
            )
        return 0

    # UniqueZoneShortcutEntry
    def ZoneId(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            return self._tab.Get(
                flatbuffers.number_types.Uint16Flags, o + self._tab.Pos
            )
        return 0


def UniqueZoneShortcutEntryStart(builder):
    builder.StartObject(2)


def UniqueZoneShortcutEntryAddHexId(builder, hexId):
    builder.PrependUint64Slot(0, hexId, 0)


def UniqueZoneShortcutEntryAddZoneId(builder, zoneId):
    builder.PrependUint16Slot(1, zoneId, 0)


def UniqueZoneShortcutEntryEnd(builder):
    return builder.EndObject()
