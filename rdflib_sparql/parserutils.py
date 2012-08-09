
from types import MethodType
from collections import OrderedDict

from pyparsing import TokenConverter, ParseResults
from rdflib_sparql.sparql import SPARQLError

from rdflib import BNode, Variable

DEBUG=True
if DEBUG: 
    import traceback

# This is an alternative 

# Comp('Sum')( Param('x')(Number) + '+' + Param('y')(Number) )

def value(ctx, val):
    
    if isinstance(val, CompValue):
        return value(ctx,val.eval(ctx))
    elif isinstance(val, list): 
        return [value(ctx,x) for x in val]
    elif isinstance(val, (BNode, Variable)):
        try: 
            return ctx[val]
        except KeyError: 
            return val
    elif isinstance(val, ParseResults) and len(val)==1:
        return value(ctx,val[0])
    else: 
        return val



class ParamValue(object): 
    def __init__(self, name, tokenList, isList): 
        self.isList=isList
        self.name=name
        if isinstance(tokenList, (list,ParseResults)) and len(tokenList)==1: 
            tokenList=tokenList[0]

        self.tokenList=tokenList

class Param(TokenConverter): 
    def __init__(self, name, expr, isList=False):
        self.name=name
        self.isList=isList
        TokenConverter.__init__(self, expr)
        self.addParseAction(self.postParse2)

    def postParse2(self, tokenList): 
        return ParamValue(self.name, tokenList, self.isList)

class ParamList(Param): 
    def __init__(self,name,expr):
        Param.__init__(self,name,expr,True)


class CompValue(OrderedDict):
    def __init__(self,name):
        
        OrderedDict.__init__(self)
        self.name=name

    def eval(self, ctx={}): 
        try: 
            self.ctx=ctx
            return self._evalfn(ctx)
        except: 
            if DEBUG:
                traceback.print_exc()
            raise SPARQLError()
        finally: 
            self.ctx=None

    def _evalfn(self, ctx): 
        # identify function to be overridden!
        return self

    def __str__(self):
        return self.name+OrderedDict.__str__(self)

    def __repr__(self):
        return self.name+OrderedDict.__repr__(self)

    def _value(self,val): 
        if self.ctx!=None: 
            return value(self.ctx, val)
        else: 
            return val
            
    def __getitem__(self,a): 
        return self._value(OrderedDict.__getitem__(self,a))

    def __getattr__(self,a):
        # Hack hack: OrderedDict relies on this
        if a=='_OrderedDict__root': raise AttributeError
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
            res._evalfn=MethodType(self.evalfn, res, CompValue)
        for t in tokenList: 
            if isinstance(t,ParamValue):
                if t.isList:
                    if not t.name in res: res[t.name]=[]
                    res[t.name].append(t.tokenList)
                else:
                    res[t.name]=t.tokenList
                #res.append(t.tokenList)
            #if isinstance(t,CompValue):
            #    res.update(t)
        return res

    def setEvalFn(self,evalfn):
        self.evalfn=evalfn
        return self
    

if __name__=='__main__':
    from pyparsing import Word, nums
    import sys

    Number = Word(nums)
    Number.setParseAction(lambda x: int(x[0]))
    Plus = Comp('plus', Param('a',Number) + '+' + Param('b',Number) )
    Plus.setEvalFn(lambda self,ctx: self.a+self.b)

    r=Plus.parseString(sys.argv[1])
    print r
    print r[0].eval({})
