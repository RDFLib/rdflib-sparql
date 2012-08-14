
from operators import and_

def findFiltersGroupGraphPattern(pattern):
    f=[]
    for p in pattern.part:
        if p.name=='Filter':
            f.append(p.expr)
    
    return f

def findFiltersQuery(query):

    filters=[]
    
    if query.having:
        filters=query.having.condition

    filters+=findFiltersGroupGraphPattern(query.where)

    if filters:
        return and_(*filters)
    
    return None
                
    
            
