from time import strftime, struct_time


class Author:
    def __init__(self, name: str, email: str, time: struct_time) -> None:
        self.name: str = name
        self.email: str = email
        self.time: struct_time = time

    def __str__(self) -> str:
        timestamp: str = strftime("%s %z", self.time)
        return f"{self.name} <{self.email}> {timestamp}"
