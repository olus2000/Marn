from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    row : int
    column : int
    position : int

    def next_row(self):
        return Location(self.row + 1, 0, self.position + 1)

    def next_column(self):
        return Location(self.row, self.column + 1, self.position + 1)


@dataclass
class MarnError: ...
