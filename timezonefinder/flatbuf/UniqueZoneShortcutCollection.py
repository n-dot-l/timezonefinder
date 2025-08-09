# UniqueZoneShortcutCollection
import flatbuffers

from timezonefinder.flatbuf.UniqueZoneShortcutEntry import UniqueZoneShortcutEntry


class UniqueZoneShortcutCollection:
    __slots__ = ["_tab"]

    @classmethod
    def GetRootAs(cls, buf, offset=0):
        n = flatbuffers.encode.Get(buf, offset)
        x = UniqueZoneShortcutCollection()
        x.Init(buf, n)
        return x

    @classmethod
    def GetRootAsUniqueZoneShortcutCollection(cls, buf, offset=0):
        return cls.GetRootAs(buf, offset)

    # UniqueZoneShortcutCollection
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # UniqueZoneShortcutCollection
    def Entries(self, j):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            x = self._tab.Vector(o)
            x += flatbuffers.number_types.UOffsetTFlags.py_type(j) * 4
            x = self._tab.Indirect(x)
            obj = UniqueZoneShortcutEntry()
            obj.Init(self._tab.Bytes, x)
            return obj
        return None

    # UniqueZoneShortcutCollection
    def EntriesLength(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.VectorLen(o)
        return 0

    # UniqueZoneShortcutCollection
    def EntriesIsNone(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        return o == 0


def UniqueZoneShortcutCollectionStart(builder):
    builder.StartObject(1)


def UniqueZoneShortcutCollectionAddEntries(builder, entries):
    builder.PrependUOffsetTRelativeSlot(
        0, flatbuffers.number_types.UOffsetTFlags.py_type(entries), 0
    )


def UniqueZoneShortcutCollectionStartEntriesVector(builder, numElems):
    return builder.StartVector(4, numElems, 4)


def UniqueZoneShortcutCollectionEnd(builder):
    return builder.EndObject()
