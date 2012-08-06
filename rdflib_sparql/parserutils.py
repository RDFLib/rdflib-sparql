
import types

from pyparsing import TokenConverter, ParseResults

# This is an alternative 

# Comp('Sum')( Param('x')(Number) + '+' + Param('y')(Number) )


class ParamValue(object): 
    def __init__(self, name, tokenList): 
        self.name=name
        if isinstance(tokenList, (list,ParseResults)) and len(tokenList)==1: tokenList=tokenList[0]
        self.tokenList=tokenList

class Param(TokenConverter): 
    def __init__(self, name, expr):
        self.name=name
        TokenConverter.__init__(self, expr)
        self.addParseAction(self.postParse2)

    def postParse2(self, tokenList): 
        return ParamValue(self.name, tokenList)

class CompValue(dict):
    def __init__(self,name):
        dict.__init__(self)
        self.name=name

    def eval(self, bindings): # identify function to be overridden!
        return None

    def __str__(self):
        return self.name+dict.__str__(self)

    def __repr__(self):
        return self.name+dict.__repr__(self)

    def __getattr__(self,a):
        try: 
            return dict.__getattr__(self,a)
        except AttributeError:
            try: 
                return self[a]
            except: 
                #raise AttributeError('no such attribute '+a)
                return None

class Comp(TokenConverter): 
    def __init__(self, name, expr): 
        TokenConverter.__init__(self, expr)
        self.name=name
        self.evalfn=None

    def postParse(self, instring, loc, tokenList):
        res=CompValue(self.name)
        if self.evalfn:
            res.eval=types.MethodType(self.evalfn, res, CompValue)
        for t in tokenList: 
            if isinstance(t,ParamValue):
                res[t.name]=t.tokenList
                #res.append(t.tokenList)
        return res

    def setEvalFn(self,evalfn):
        self.evalfn=evalfn

    

if __name__=='__main__':
    from pyparsing import Word, nums
    import sys

    Number = Word(nums)
    Number.setParseAction(lambda x: int(x[0]))
    Plus = Comp('plus', Param('a',Number) + '+' + Param('b',Number) )
    Plus.setEvalFn(lambda self,bindings: self.a+self.b)

    r=Plus.parseString(sys.argv[1])
    print r
    print r[0].eval({})
