import os
import json
from datetime import datetime

class FileManager:
    def __init__(self, database=None):
        self.database = database or []

    def create_report(self):
        folder_name = "reports"
        current_datetime = datetime.now().replace(microsecond=0)
        formatted_datetime = current_datetime.strftime("%y-%m-%d_%Hh%Mm%Ss")
        base_filename = f"{formatted_datetime}_report"
        current_directory = os.getcwd()
        folder_path = os.path.join(current_directory, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        txt_path = os.path.join(folder_path, base_filename + ".txt")
        json_path = os.path.join(folder_path, base_filename + ".json")

        with open(txt_path, "w", encoding="utf-8") as ftxt:
            for elem in self.database:
                # Expect elem to be a dict like {"ip": "1.2.3.4", "status": "...", ...}
                lines = []
                for k, v in elem.items():
                    lines.append(f"{k}: {v}")
                ftxt.write("\n".join(lines) + "\n")

        with open(json_path, "w", encoding="utf-8") as fjson:
            json.dump(self.database, fjson, ensure_ascii=False, indent=2)

        return {"txt": txt_path, "json": json_path}
