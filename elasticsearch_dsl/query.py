from six import add_metaclass

from .utils import DslMeta, DslBase

class QueryMeta(DslMeta):
    _classes = {}

def Q(name_or_query, **params):
    if isinstance(name_or_query, dict):
        if params:
            raise #XXX
        if len(name_or_query) != 1:
            raise #XXX
        name, params = name_or_query.popitem()
        return Query.get_dsl_class(name)(**params)
    if isinstance(name_or_query, Query):
        if params:
            raise #XXX
        return name_or_query
    return Query.get_dsl_class(name_or_query)(**params)

@add_metaclass(QueryMeta)
class Query(DslBase):
    _type_name = 'query'
    _type_shortcut = staticmethod(Q)
    name = None

    def __add__(self, other):
        # make sure we give queries that know how to combine themselves
        # preference
        if hasattr(other, '__radd__'):
            return other.__radd__(self)
        return Bool(must=[self, other])

    def __invert__(self):
        return Bool(must_not=[self])

    def __or__(self, other):
        # make sure we give queries that know how to combine themselves
        # preference
        if hasattr(other, '__ror__'):
            return other.__ror__(self)
        return Bool(should=[self, other])

    def __and__(self, other):
        # make sure we give queries that know how to combine themselves
        # preference
        if hasattr(other, '__rand__'):
            return other.__rand__(self)
        return Bool(must=[self, other])

class MatchAll(Query):
    name = 'match_all'
    def __add__(self, other):
        return other._clone()
    __and__ = __rand__ = __radd__ = __add__

    def __or__(self, other):
        return self
    __ror__ = __or__

EMPTY_QUERY = MatchAll()

class Match(Query):
    name = 'match'

class Bool(Query):
    name = 'bool'
    _param_defs = {
        'must': {'type': 'query', 'multi': True},
        'should': {'type': 'query', 'multi': True},
        'must_not': {'type': 'query', 'multi': True},
    }

    def __add__(self, other):
        q = self._clone()
        if isinstance(other, Bool):
            q.must += other.must
            q.should += other.should
            q.must_not += other.must_not
        else:
            q.must.append(other)
        return q
    __radd__ = __add__

    def __or__(self, other):
        if not (self.must or self.must_not):
            # TODO: if only 1 in must or should, append the query instead of other
            q = self._clone()
            q.should.append(other)
            return q

        elif isinstance(other, Bool) and not (other.must or other.must_not):
            # TODO: if only 1 in must or should, append the query instead of self
            q = other._clone()
            q.should.append(self)
            return q

        return super(Bool, self).__or__(other)
    __ror__ = __or__

    def __invert__(self):
        # special case for single negated query
        if not (self.must or self.should) and len(self.must_not) == 1:
            return self.must_not[0]._clone()

        # bol without should, just flip must and must_not
        elif not self.should:
            q = self._clone()
            q.must, q.must_not = q.must_not, q.must
            return q

        # TODO: should -> must_not.append(Bool(should=self.should)) ??
        # queries with should just invert normally
        return super(Bool, self).__invert__()