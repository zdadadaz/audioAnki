import json

class json_io:
    def read(self):
        with open('file.json', 'r') as f:
            tmp =json.loads(f.read())
            return tmp
    def save_userid(self,input):
        with open('file.json', 'w') as f:
            return json.dump(input, f)
