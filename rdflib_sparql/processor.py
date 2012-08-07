


class Bindings(dict):
    def __init__(self, outer=None): 
        self.outer=outer
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except: 
            if not self.outer: raise
            return self.outer[key]
        

class QueryContext(object): 

    def __init__(self): 
        self.bindings=Bindings()

    def __getitem__(self, key):
        return self.bindings[key]

    def push(self):
        self.bindings=Bindings(self.bindings)
        
    def pop(self):
        self.bindings=self.bindings.outer
        if self.bindings==None:
            raise "We've bottomed out of the bindings stack!"
