class Summarizer:
    def compress(self, updates: list[str]) -> str:
        if not updates:
            return ""
        return updates[-1]
