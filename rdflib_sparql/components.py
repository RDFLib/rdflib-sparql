
class pname:
    def __init__(self, prefix, localname):
        self.prefix=prefix
        self.localname=localname

    def __str__(self):
        return "pname(%s,%s)"%(self.prefix, self.localname)

    def __repr__(self):
        return str(self)
