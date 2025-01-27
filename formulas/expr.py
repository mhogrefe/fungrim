# -*- coding: utf-8 -*-

int_types = (int, type(1<<128))

katex_function = []

int_cache = {}

class Expr(object):
    """
    Represents a symbolic expression.

    A symbolic expression is either an atom (symbol, integer or text)
    or a non-atomic expression representing a function application
    f(a, b, ...) where f and a, b, ... are symbolic expressions.

    The methods .is_atom(), and specifically .is_symbol(), .is_integer(),
    .is_text() are useful to check for atoms.

    For a non-atomic expression expr, expr.head() returns f and
    expr.args() returns (a, b, ...) as a Python tuple.
    For a non-atomic expression, these methods both return None.

    Expr objects are immutable and instances may be cached silently.

    Most arithmetic operators are overloaded to permit constructing
    expressions in natural syntax, but the == and != operators
    perform structural comparison.
    """

    def __new__(self, arg=None, symbol_name=None, call=None):
        """
        Expr(expr) creates a copy of expr (this may actually return
        the same object).

        Expr(5) creates an Integer atom with the value 5.
        Expr("text") creates a Text atom with the value "text".
        Expr(symbol_name="x") creates a Symbol atom with the label "x".

        Expr(call=(f, a, b)) creates the non-atomic expression f(a, b).
        """
        if isinstance(arg, Expr):
            return arg
        self = object.__new__(Expr)
        self._hash = None
        self._symbol = None
        self._integer = None
        self._text = None
        self._args = None
        if symbol_name is not None:
            self._symbol = symbol_name
        elif isinstance(arg, str):
            self._text = arg
        elif isinstance(arg, int_types):
            self._integer = int(arg)
        elif call is not None:
            assert len(call) >= 1
            self._args = tuple(Expr(obj) for obj in call)
        return self

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        if hash(self) != hash(other):
            return False
        if self._args is not None:
            if other._args is not None:
                return self._args == other._args
            return False
        if self._symbol is not None:
            if other._symbol is not None:
                return self._symbol == other._symbol
            return False
        if self._integer is not None:
            if other._integer is not None:
                return self._integer == other._integer
            return False
        if self._text is not None:
            if other._text is not None:
                return self._text == other._text
            return False
        return False

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        if self._hash is None:
            if self._symbol is not None:
                self._hash = hash(self._symbol)
            elif self._integer is not None:
                self._hash = hash(self._integer)
            elif self._text is not None:
                self._hash = hash(self._text)
            else:
                self._hash = hash(self._args)
        return self._hash

    def is_atom(self):
        """Returns True if self is an atom (symbol, integer or text),
        False otherwise."""
        return self._args is None

    def is_symbol(self):
        return self._symbol is not None

    def is_integer(self):
        return self._integer is not None

    def is_text(self):
        return self._text is not None

    def head(self):
        if self._args is None:
            return None
        return self._args[0]

    def args(self):
        if self._args is None:
            return None
        return self._args[1:]

    def __call__(self, *args):
        return Expr(call=((self,) + args))

    def __pos__(self):
        return Pos(self)
    def __neg__(self):
        return Neg(self)
    def __abs__(self):
        return Abs(self)

    def __add__(self, other):
        return Add(Expr(self), Expr(other))
    def __radd__(self, other):
        return Add(Expr(other), Expr(self))

    def __sub__(self, other):
        return Sub(Expr(self), Expr(other))
    def __rsub__(self, other):
        return Sub(Expr(other), Expr(self))

    def __mul__(self, other):
        return Mul(Expr(self), Expr(other))
    def __rmul__(self, other):
        return Mul(Expr(other), Expr(self))

    def __div__(self, other):
        return Div(Expr(self), Expr(other))
    def __rdiv__(self, other):
        return Div(Expr(other), Expr(self))
    def __truediv__(self, other):
        return Div(Expr(self), Expr(other))
    def __rtruediv__(self, other):
        return Div(Expr(other), Expr(self))

    def __pow__(self, other):
        return Pow(Expr(self), Expr(other))
    def __rpow__(self, other):
        return Pow(Expr(other), Expr(self))

    def str(self, level=0, **kwargs):
        if self._symbol is not None:
            s = str(self._symbol)
        elif self._integer is not None:
            s = str(self._integer)
        elif self._text is not None:
            s = self._text.replace('"', '\\"')
            return '"' + s + '"'
        elif self._args is not None:
            fstr = self._args[0].str(level, **kwargs)
            argstrs = [arg.str(level+1, **kwargs) for arg in self._args[1:]]
            if self._args[0] is Entry:
                s = fstr + "(" + ",\n    ".join(argstrs) + ")"
            else:
                s = fstr + "(" + ", ".join(argstrs) + ")"
        else:
            raise ValueError("no content")
        return s

    def __str__(self):
        return self.str()

    def __repr__(self):
        return self.str()

    def _all_symbols(self):
        if self._symbol is not None:
            return [self]
        symbols = []
        if self._args is not None:
            for arg in self._args:
                arg_symbols = arg._all_symbols()
                for s in arg_symbols:
                    symbols.append(s)
        return symbols

    def all_symbols(self):
        from collections import OrderedDict
        symbols = self._all_symbols()
        return list(OrderedDict.fromkeys(symbols))

    # needs work
    def need_parens_in_mul(self):
        if self.is_atom():
            if self.is_integer() and self._integer < 0:
                return True
            return False
        # if self._args[0] in (Pos, Neg):
        #     return True
        if self._args[0] in (Add, Sub):
            return True
        return False

    # needs work
    def show_exponential_as_power(self, allow_div=True):
        if self.is_atom():
            return True
        head = self._args[0]
        if head is Div:
            if not self._args[-1].is_atom():
                return False
            allow_div = False
        if head not in (Pos, Neg, Add, Sub, Mul, Div, Pow, Abs, Sqrt):
            return False
        for arg in self._args[1:]:
            if not arg.show_exponential_as_power(allow_div=allow_div):
                return False
        return True

    def latex(self, in_small=False, __cache={}):
        if (self, in_small) in __cache:
            return __cache[(self, in_small)]
        else:
            tex = self._latex(in_small=in_small)
            __cache[(self, in_small)] = tex
            return tex

    def _latex(self, in_small=False):

        if self in symbol_latex_table:
            return symbol_latex_table[self]

        if self.is_atom():
            if self._symbol is not None:
                if self._symbol in variable_names:
                    if len(self._symbol) == 1:
                        return self._symbol
                    else:
                        if self._symbol == "epsilon":
                            return "\\varepsilon"
                        return "\\" + self._symbol
                return "\\operatorname{" + self._symbol + "}"
            if self._integer is not None:
                return str(self._integer)
            if self._text is not None:
                return "\\text{``" + str(self._text).replace("_","\\_") + "''}"
            raise NotImplementedError

        head = self._args[0]
        args = self._args[1:]

        if head in infix_latex_table:
            argstr = [arg.latex(in_small=in_small) for arg in args]
            return (" " + infix_latex_table[head] + " ").join(argstr)

        # F(n,x,...) -> F_n(x,...)
        if head in subscript_call_latex_table:
            arg0 = args[0].latex(in_small=True)
            args1 = ", ".join(arg.latex(in_small=in_small) for arg in args[1:])
            return subscript_call_latex_table[head] + "_{" + arg0 + "}" + "\!\\left(" + args1 + "\\right)"

        if head is Exp:
            assert len(args) == 1
            if args[0].show_exponential_as_power():
                return Pow(ConstE, args[0]).latex(in_small=in_small)

        if head is Div:
            assert len(args) == 2
            num, den = args
            if in_small:
                numstr = num.latex(in_small=True)
                denstr = den.latex(in_small=True)
                if num.need_parens_in_mul():  # fixme!
                    numstr = "\\left( %s \\right)" % numstr
                if den.need_parens_in_mul():  # fixme!
                    denstr = "\\left( %s \\right)" % denstr
                return numstr + " / " + denstr
            else:
                numstr = num.latex()
                denstr = den.latex()
                #if num.is_integer() and den.is_integer():
                #    return "\\frac{" + numstr + "}{" + denstr + "}"
                #else:
                return "\\frac{" + numstr + "}{" + denstr + "}"

        argstr = [arg.latex(in_small=in_small) for arg in args]
        if head is Where:
            return argstr[0] + "\; \\text{ where } " + ",\,".join(argstr[1:])
        if head is Pos:
            assert len(args) == 1
            return "+" + argstr[0]
        if head is Neg:
            assert len(args) == 1
            return "-" + argstr[0]
        if head is Add:
            return " + ".join(argstr)
        if head is Sub:
            for i in range(1, len(args)):
                if not args[i].is_atom() and args[i]._args[0] in (Neg, Sub):
                    argstr[i] = "\\left(" + argstr[i] + "\\right)"
            return " - ".join(argstr)
        if head is Mul:
            for i in range(len(args)):
                if args[i].need_parens_in_mul():
                    argstr[i] = "\\left(" + argstr[i] + "\\right)"
            return " ".join(argstr)
        if head is Pow:
            assert len(args) == 2
            # remove frac to try to keep it on one line
            base = args[0]
            expo = args[1]
            # todo: more systematic solutions
            if not base.is_atom() and base.head() in (Sin, Cos, Csc, Tan, Sinh, Cosh, Tanh, DedekindEta):
                return base.head().latex() + "^{" + expo.latex(in_small=True) + "}" + "\\!\\left(" + base.args()[0].latex(in_small=in_small) + "\\right)"
            if not base.is_atom() and base.head() is Fibonacci:
                return "F_{%s}^{%s}" % (base.args()[0].latex(in_small=in_small), expo.latex(in_small=True))
            if not base.is_atom() and base.head() in (JacobiTheta1, JacobiTheta2, JacobiTheta3, JacobiTheta4) and len(base.args()) == 2:
                return base.head().latex() + "^{%s}\\!\\left(%s, %s\\right)" % (expo.latex(in_small=True), base.args()[0].latex(), base.args()[1].latex())
            if not base.is_atom() and base.head() in subscript_call_latex_table and len(base.args()) == 2:
                h = subscript_call_latex_table[base.head()]
                s = base.args()[0].latex(in_small=True)
                e = expo.latex(in_small=True)
                v = base.args()[1].latex(in_small=in_small)
                return "%s_{%s}^{%s}\\!\\left(%s\\right)" % (h, s, e, v)
            basestr = base.latex(in_small=in_small)
            expostr = expo.latex(in_small=True)
            if base.is_symbol() or (base.is_integer() and base._integer >= 0) or (not base.is_atom() and base._args[0] in (Abs, Binomial, PrimeNumber, Matrix2x2, Parentheses, Braces, Brackets)):
                return "{" + basestr + "}^{" + expostr + "}"
            else:
                return "{\\left(" + basestr + "\\right)}^{" + expostr + "}"
        if head is Integral:
            assert len(args) == 2
            assert args[1]._args[0] is Tuple
            _, var, low, high = args[1]._args
            var = var.latex()
            low = low.latex(in_small=True)
            high = high.latex(in_small=True)
            return "\\int_{%s}^{%s} %s \, d%s" % (low, high, argstr[0], var)
        if head in (IndefiniteIntegralEqual, RealIndefiniteIntegralEqual, ComplexIndefiniteIntegralEqual):
            # IndefiniteIntegralEqual(f(z), g(z), z, c)
            if len(args) == 3:
                fx, gx, x = args
                fx = argstr[0]
                gx = argstr[1]
                x = argstr[2]
                return "\\int %s \, d%s = %s + \\mathcal{C}" % (fx, x, gx)
            elif len(args) == 4:
                fx, gx, x, c = args
                fx = argstr[0]
                gx = argstr[1]
                x = argstr[2]
                if x == c:
                    return "\\int %s \, d%s = %s + \\mathcal{C}" % (fx, x, gx)
                else:
                    return "\\int %s \, d%s = %s + \\mathcal{C}, %s = %s" % (fx, x, gx, x, c)
            else:
                raise ValueError
        if head in (Sum, Product):
            # Sum(f(n), Tuple(n, a, b))
            # Sum(f(n), Tuple(n, a, b), P(n)) ???
            # Sum(f(n), n, P(n))
            if head is Sum:
                ss = "\\sum"
            else:
                ss = "\\prod"
            # todo: auto-parenthesis for Add/...?
            if len(args) == 2 and not args[1].is_atom() and args[1]._args[0] is Tuple:
                _, var, low, high = args[1]._args
                var = var.latex()
                low = low.latex(in_small=True)
                high = high.latex(in_small=True)
                return ss + ("_{%s=%s}^{%s} %s" % (var, low, high, argstr[0]))
            elif len(args) == 2:
                func, var = args
                return ss + ("_{%s} %s" % (var, argstr[0]))
            elif len(args) == 3:
                func, var, cond = args
                cond = cond.latex(in_small=True)
                return ss + ("_{%s} %s" % (cond, argstr[0]))
            else:
                raise ValueError
        if head in (DivisorSum, DivisorProduct):
            if len(args) == 3:
                formula, var, number = args
                formula = argstr[0]
                var = var.latex()
                number = number.latex(in_small=True)
                ss = "_{%s \\mid %s} %s" % (var, number, formula)
            elif len(args) == 4:
                formula, var, number, cond = args
                formula = argstr[0]
                var = var.latex()
                number = number.latex(in_small=True)
                cond = cond.latex(in_small=True)
                #ss = "_{\\begin{matrix} {\\scriptstyle %s \\mid %s} \\\\ {\\scriptstyle %s} \\end{matrix}} %s" % (var, number, cond, formula)
                ss = "_{%s \\mid %s,\\, %s} %s" % (var, number, cond, formula)
            else:
                raise ValueError
            if head is DivisorSum:
                return "\\sum" + ss
            else:
                return "\\prod" + ss
        if head in (PrimeSum, PrimeProduct):
            if len(args) == 2:
                formula, var = args
                formula = argstr[0]
                var = var.latex()
                ss = "_{%s} %s" % (var, formula)
            elif len(args) == 3:
                formula, var, cond = args
                formula = argstr[0]
                var = var.latex()
                cond = cond.latex(in_small=True)
                ss = "_{%s} %s" % (cond, formula)
            else:
                raise ValueError
            if head is PrimeSum:
                return "\\sum" + ss
            else:
                return "\\prod" + ss
        if head in (Limit, SequenceLimit, RealLimit, LeftLimit, RightLimit, ComplexLimit, MeromorphicLimit):
            if len(args) == 3:
                formula, var, point = args
                cond = ""
            elif len(args) == 4:
                formula, var, point, cond = args
                cond = ", " + cond.latex(in_small=True)
            else:
                raise ValueError
            var = var.latex()
            point = point.latex(in_small=True)
            formula = formula.latex()
            if (not args[2].is_atom() and args[2].head() not in [Abs]):
                formula = "\\left[ %s \\right]" % formula
            if head is LeftLimit:
                s = "\\lim_{%s \\to {%s}^{-}%s} %s" % (var, point, cond, formula)
            elif head is RightLimit:
                s = "\\lim_{%s \\to {%s}^{+}%s} %s" % (var, point, cond, formula)
            else:
                s = "\\lim_{%s \\to %s%s} %s" % (var, point, cond, formula)
            return s
        if head in (Minimum, Maximum, ArgMin, ArgMax, ArgMinUnique, ArgMaxUnique, Supremum, Infimum, Zeros, UniqueZero, Solutions, UniqueSolution):
            opname = {Minimum:"\\min", Maximum:"\\max",
                      ArgMin:"\\operatorname{arg\,min}",ArgMinUnique:"\\operatorname{arg\,min*}",
                      ArgMax:"\\operatorname{arg\,max}",ArgMaxUnique:"\\operatorname{arg\,max*}",
                      Infimum:"\\operatorname{inf}", Supremum:"\\operatorname{sup}",
                      Zeros:"\\operatorname{zeros}\\,", UniqueZero:"\\operatorname{zero*}\\,",
                      Solutions:"\\operatorname{solutions}\\,", UniqueSolution:"\\operatorname{solution*}\\,"}[head]
            if head in (Minimum, Maximum, Supremum, Infimum) and len(args) == 1:
                return "%s\\left(%s\\right)" % (opname, argstr[0])
            assert len(args) == 3
            formula, var, predicate = args
            #var = var.latex()
            if 0 and predicate.head() is And and len(predicate.args()) > 1:
                # katex does not support substack
                predicate = "\\begin{matrix}" + "\\\\".join("\\scriptstyle %s " % s.latex(in_small=True) for s in predicate.args()) + "\\end{matrix}"
            else:
                predicate = predicate.latex(in_small=True)
            if formula.head() in (Add, Sub):
                formula = "\\left(" + formula.latex() + "\\right)"
            else:
                formula = formula.latex()
            return "\\mathop{%s}\\limits_{%s} %s" % (opname, predicate, formula)
        if head is ComplexZeroMultiplicity:
            assert len(args) == 3
            f, var, point = argstr
            if args[1] == args[2]:
                return "\\mathop{\\operatorname{ord}}\\limits_{%s} %s" % (point, f)
            else:
                return "\\mathop{\\operatorname{ord}}\\limits_{%s=%s} %s" % (var, point, f)
        if head is Residue:
            assert len(args) == 3
            f, var, point = argstr
            if args[1] == args[2]:
                return "\\mathop{\\operatorname{Res}}\\limits_{%s} %s" % (point, f)
            else:
                return "\\mathop{\\operatorname{Res}}\\limits_{%s=%s} %s" % (var, point, f)
        if head in (Derivative, RealDerivative, ComplexDerivative, ComplexBranchDerivative, MeromorphicDerivative):
            if len(args) == 2:
                assert args[1]._args[0] is Tuple
                _, var, point, order = args[1]._args
            elif len(args) == 3:
                _, var, point = args
                order = Expr(1)
            elif len(args) == 4:
                _, var, point, order = args
            if not args[0].is_atom():
                f = args[0].head()
                if f.is_symbol() and f not in (Exp, Sqrt) and args[0].args() == (var,):
                    pointstr = point.latex(in_small=True)
                    fstr = args[0].head().latex()
                    if order.is_integer() and order._integer == 0:
                        return "%s(%s)" % (fstr, pointstr)
                    if order.is_integer() and order._integer == 1:
                        return "%s'(%s)" % (fstr, pointstr)
                    if order.is_integer() and order._integer == 2:
                        return "%s''(%s)" % (fstr, pointstr)
                    if order.is_integer() and order._integer == 3:
                        return "%s'''(%s)" % (fstr, pointstr)
                    return "{%s}^{(%s)}(%s)" % (fstr, order.latex(), pointstr)
                if 1 and (f in subscript_call_latex_table and len(args[0].args()) == 2 and args[0].args()[1] == var):
                    arg0 = args[0].args()[0].latex(in_small=True)
                    fstr = subscript_call_latex_table[f]
                    pointstr = point.latex(in_small=True)
                    if order.is_integer() and order._integer == 0:
                        return "%s_{%s}(%s)" % (fstr, arg0, pointstr)
                    if order.is_integer() and order._integer == 1:
                        return "%s'_{%s}(%s)" % (fstr, arg0, pointstr)
                    if order.is_integer() and order._integer == 2:
                        return "%s''_{%s}(%s)" % (fstr, arg0, pointstr)
                    if order.is_integer() and order._integer == 3:
                        return "%s'''_{%s}(%s)" % (fstr, arg0, pointstr)
                    return "{%s}^{(%s)}_{%s}(%s)" % (fstr, order.latex(), arg0, pointstr)
            varstr = var.latex()
            pointstr = point.latex(in_small=True)
            orderstr = order.latex()
            if var is point:
                if order.is_integer() and order._integer == 1:
                    return "\\frac{d}{d %s}\, %s" % (varstr, argstr[0])
                else:
                    return "\\frac{d^{%s}}{{d %s}^{%s}} %s" % (orderstr, varstr, orderstr, argstr[0])
            else:
                if order.is_integer() and order._integer == 1:
                    return "\\left[ \\frac{d}{d %s}\, %s \\right]_{%s = %s}" % (varstr, argstr[0], varstr, pointstr)
                else:
                    return "\\left[ \\frac{d^{%s}}{{d %s}^{%s}} %s \\right]_{%s = %s}" % (orderstr, varstr, orderstr, argstr[0], varstr, pointstr)
        if head is Sqrt:
            assert len(args) == 1
            return "\\sqrt{" + argstr[0] + "}"
        if head is Abs:
            assert len(args) == 1
            return "\\left|" + argstr[0] + "\\right|"
        if head is Floor:
            assert len(args) == 1
            return "\\left\\lfloor " + argstr[0] + " \\right\\rfloor"
        if head is Ceil:
            assert len(args) == 1
            return "\\left\\lceil " + argstr[0] + " \\right\\rceil"
        if head is Tuple:
            return "\\left(" + ", ".join(argstr) + "\\right)"
        if head is Set:
            return "\\left\{" + ", ".join(argstr) + "\\right\}"
        if head is List:
            return "\\left[" + ", ".join(argstr) + "\\right]"
        # todo: unify subscript cases
        if head is BernoulliB:
            assert len(args) == 1
            return "B_{" + argstr[0] + "}"
        if head is Fibonacci:
            assert len(args) == 1
            return "F_{" + args[0].latex(in_small=True) + "}"
        if head is BellNumber:
            assert len(args) == 1
            return "B_{" + argstr[0] + "}"
        if head is HarmonicNumber:
            assert len(args) == 1
            return "H_{" + argstr[0] + "}"
        if head is PrimeNumber:
            assert len(args) == 1
            return "p_{" + argstr[0] + "}"
        if head is RiemannZetaZero:
            assert len(args) == 1
            return "\\rho_{" + argstr[0] + "}"
        if head is DirichletLZero:
            assert len(args) == 2
            return "\\rho_{%s, %s}" % (argstr[0], argstr[1])
        if head is LegendrePolynomialZero:
            assert len(args) == 2
            return "x_{%s,%s}" % (argstr[0], argstr[1])
        if head is GaussLegendreWeight:
            assert len(args) == 2
            return "w_{%s,%s}" % (argstr[0], argstr[1])
        if head is GeneralizedBernoulliB:
            assert len(args) == 2
            return "B_{%s,%s}" % (argstr[0], argstr[1])
        if head in (BesselJ, BesselY, BesselI, BesselK, HankelH1, HankelH2):
            assert len(args) == 2
            n, z = args
            nstr = n.latex(in_small=True)
            zstr = z.latex(in_small)
            fsym = {BesselJ:"J", BesselI:"I", BesselY:"Y", BesselK:"K", HankelH1:"H^{(1)}", HankelH2:"H^{(2)}"}[head]
            return fsym + "_{" + nstr + "}" + "\!\\left(" + zstr + "\\right)"
        if head in (BesselJDerivative, BesselYDerivative, BesselIDerivative, BesselKDerivative):
            assert len(args) == 3
            n, z, r = args
            nstr = n.latex(in_small=True)
            zstr = z.latex(in_small)
            rstr = r.latex(in_small)
            fsym = {BesselJDerivative:"J", BesselIDerivative:"I", BesselYDerivative:"Y", BesselKDerivative:"K", HankelH1:"H^{(1)}", HankelH2:"H^{(2)}"}[head]
            if r.is_integer() and r._integer >= 0 and r._integer <= 3:
                return fsym + ("'" * r._integer) + "_{" + nstr + "}" + "\!\\left(" + zstr + "\\right)"
            else:
                return fsym + "^{(" + rstr + ")}_{" + nstr + "}" + "\!\\left(" + zstr + "\\right)"
        if head in (CoulombF, CoulombG):
            assert len(args) == 3
            l, eta, z = args
            lstr = l.latex(in_small=True)
            etastr = eta.latex(in_small=True)
            zstr = z.latex()
            F = {CoulombF:"F", CoulombG:"G"}[head]
            return F + ("_{%s,%s}\!\\left(" % (lstr, etastr)) + zstr + "\\right)"
        if head is CoulombH:
            assert len(args) == 4
            omega, l, eta, z = args
            if omega.is_integer():
                omegastr = "+"
                if omega._integer == -1:
                    omegastr = "-"
            else:
                omegastr = omega.latex(in_small=True)
            lstr = l.latex(in_small=True)
            etastr = eta.latex(in_small=True)
            zstr = z.latex()
            return "H" + ("^{%s}_{%s,%s}\!\\left(" % (omegastr, lstr, etastr)) + zstr + "\\right)"
        if head is CoulombC:
            l, eta = args
            lstr = l.latex(in_small=True)
            etastr = eta.latex()
            return "C_{%s}\!\\left(%s\\right)" % (lstr, etastr)
        if head is CoulombSigma:
            l, eta = args
            lstr = l.latex(in_small=True)
            etastr = eta.latex()
            return "\\sigma_{%s}\!\\left(%s\\right)" % (lstr, etastr)
        if head in (Factorial, DoubleFactorial):
            assert len(args) == 1
            ss = "!"
            if head is DoubleFactorial:
                ss += "!"
            if args[0].is_symbol() or (args[0].is_integer() and args[0]._integer >= 0):
                return argstr[0] + " " + ss
            else:
                return "\\left(" + argstr[0] + "\\right)" + ss
        if head is RisingFactorial:
            assert len(args) == 2
            return "\\left(" + argstr[0] + "\\right)_{" + argstr[1] + "}"
        if head is FallingFactorial:
            assert len(args) == 2
            return "\\left(" + argstr[0] + "\\right)^{\\underline{" + argstr[1] + "}}"
        if head is Binomial:
            assert len(args) == 2
            return "{" + argstr[0] + " \\choose " + argstr[1] + "}"
        if head is StirlingCycle:
            assert len(args) == 2
            return "\\left[{%s \\atop %s}\\right]" % (argstr[0], argstr[1])
        if head is StirlingS1:
            assert len(args) == 2
            return "s\!\\left(%s, %s\\right)" % (argstr[0], argstr[1])
        if head is StirlingS2:
            assert len(args) == 2
            return "\\left\\{{%s \\atop %s}\\right\\}" % (argstr[0], argstr[1])
        if head is LambertW:
            assert len(args) in (2,3)
            if len(args) == 2:
                n, z = args
                nstr = n.latex(in_small=True)
                zstr = z.latex(in_small)
                return "W_{" + nstr + "}" + "\!\\left(" + zstr + "\\right)"
            else:
                n, z, r = args
                nstr = n.latex(in_small=True)
                zstr = z.latex(in_small)
                rstr = r.latex(in_small)
                if r.is_integer() and r._integer >= 0 and r._integer <= 3:
                    return "W" + ("'" * r._integer) + "_{" + nstr + "}" + "\!\\left(" + zstr + "\\right)"
                else:
                    return "W" + "^{(" + rstr + ")}_{" + nstr + "}" + "\!\\left(" + zstr + "\\right)"
        if head is LambertWPuiseuxCoefficient:
            assert len(args) == 1
            return "{\\mu}_{" + argstr[0] + "}"
        if head is AsymptoticTo:
            assert len(argstr) == 4
            return "%s \\sim %s, \; %s \\to %s" % tuple(argstr)
        if head is And:
            for i in range(len(args)):
                if (not args[i].is_atom()) and args[i].head() in (And, Or):
                    argstr[i] = "\\left(%s\\right)" % argstr[i]
            if in_small:
                # see ff190c
                #return "\\text{ and }".join(argstr)
                return ",\\,".join(argstr)
            else:
                return " \\,\\mathbin{\\operatorname{and}}\\, ".join(argstr)
                #return " \\,\\land\\, ".join(argstr)
        if head is Or:
            for i in range(len(args)):
                if (not args[i].is_atom()) and args[i].head() in (And, Or, Not):
                    argstr[i] = "\\left(%s\\right)" % argstr[i]
            return " \\,\\mathbin{\\operatorname{or}}\\, ".join(argstr)
            #return " \\,\\lor\\, ".join(argstr)
        if head is Not:
            assert len(args) == 1
            return " \\operatorname{not} \\left(%s\\right)" % argstr[0]
            #return " \\neg \\left(%s\\right)" % argstr[0]
        if head is Implies:
            return " \\implies ".join("\\left(%s\\right)" % s for s in argstr)
        if head is Equivalent:
            return " \\iff ".join("\\left(%s\\right)" % s for s in argstr)
        if head is EqualAndElement:
            assert len(args) == 3
            return "%s = %s \\in %s" % (argstr[0], argstr[1], argstr[2])
        if head is KroneckerDelta:
            assert len(args) == 2
            xstr = args[0].latex(in_small=True)
            ystr = args[1].latex(in_small=True)
            return "\delta_{(%s,%s)}" % (xstr, ystr)
        if head in (LegendreSymbol, JacobiSymbol, KroneckerSymbol):
            if 0 and in_small:
                return "(%s \\mid %s)" % (argstr[0], argstr[1])
            else:
                return "\\left( \\frac{%s}{%s} \\right)" % (argstr[0], argstr[1])
        if head is CongruentMod:
            return "%s \\equiv %s \\pmod {%s}" % (argstr[0], argstr[1], argstr[2])
        if head is Odd:
            return "%s \\text{ odd}" % (argstr[0])
        if head is Even:
            return "%s \\text{ even}" % (argstr[0])
        if head is ZZGreaterEqual:
            assert len(args) == 1
            # if args[0].is_integer():
            #    return "\{%s, %s, \ldots\}" % (args[0]._integer, args[0]._integer + 1)
            return "\\mathbb{Z}_{\ge %s}" % argstr[0]
        if head is ZZLessEqual:
            assert len(args) == 1
            if args[0].is_integer():
                return "\{%s, %s, \ldots\}" % (args[0]._integer, args[0]._integer - 1)
            return "\\mathbb{Z}_{\le %s}" % argstr[0]
        if head is ZZBetween:
            assert len(args) == 2
            if args[0].is_integer():
                return "\{%s, %s, \ldots %s\}" % (argstr[0], args[0]._integer + 1, argstr[1])
            else:
                return "\{%s, %s + 1, \ldots %s\}" % (argstr[0], argstr[0], argstr[1])
        if head in (ClosedInterval, OpenInterval, ClosedOpenInterval, OpenClosedInterval):
            assert len(args) == 2
            #arg0 = args[0].latex(in_small=True)
            #arg1 = args[1].latex(in_small=True)
            arg0 = args[0].latex(in_small=in_small)
            arg1 = args[1].latex(in_small=in_small)
            if head is ClosedInterval:
                return "\\left[%s, %s\\right]" % (arg0, arg1)
            if head is OpenInterval:
                return "\\left(%s, %s\\right)" % (arg0, arg1)
            if head is ClosedOpenInterval:
                return "\\left[%s, %s\\right)" % (arg0, arg1)
            if head is OpenClosedInterval:
                return "\\left(%s, %s\\right]" % (arg0, arg1)
        if head is RealBall:
            assert len(args) == 2
            return "\\left[%s \\pm %s\\right]" % (args[0].latex(in_small=True), args[1].latex(in_small=True))
        if head is BernsteinEllipse:
            assert len(args) == 1
            return "\\mathcal{E}_{" + argstr[0] + "}"
        if head is Lattice:
            return "\\Lambda_{(%s)}" % (", ".join(argstr))
        if head is DomainCodomain:
            assert len(args) == 2
            #return "%s \\rightarrow %s" % (argstr[0], argstr[1])
        if head is Conjugate:
            assert len(args) == 1
            return "\\overline{%s}" % argstr[0]
        if head is SetBuilder:
            assert len(args) == 3
            return "\\left\\{ %s : %s \\right\\}" % (argstr[0], argstr[2])
        if head is Cardinality:
            assert len(args) == 1
            #return "\\text{card }" + argstr[0]
            return "\\# " + argstr[0]
            #return "\\left|" + argstr[0] + "\\right|"
        if head is Decimal:
            assert len(args) == 1
            text = args[0]._text
            if "e" in text:
                mant, expo = text.split("e")
                expo = expo.lstrip("+")
                text = mant + " \\cdot 10^{" + expo + "}"
            return text
        if head is Matrix2x2:
            assert len(args) == 4
            return r"\begin{pmatrix} %s & %s \\ %s & %s \end{pmatrix}" % tuple(argstr)
        if head is Matrix2x1:
            assert len(args) == 2
            return r"\begin{pmatrix} %s \\ %s \end{pmatrix}" % tuple(argstr)
        if head is ModularGroupAction:
            assert len(args) == 2
            return "%s \\circ %s" % tuple(argstr)
        if head is PrimitiveReducedPositiveIntegralBinaryQuadraticForms:
            assert len(args) == 1
            return "\\mathcal{Q}^{*}_{%s}" % argstr[0]
        if head is HypergeometricUStarRemainder:
            assert len(args) == 4
            return "R_{%s}\!\\left(%s,%s,%s\\right)" % tuple(argstr)
        if head is DirichletCharacter:
            if len(args) == 2:
                return "\\chi_{%s}(%s, \\cdot)" % tuple(argstr)
            elif len(args) == 3:
                return "\\chi_{%s}(%s, %s)" % tuple(argstr)
            else:
                raise ValueError
        if head is DirichletGroup:
            #return "\\{\\chi_{%s}\\}" % argstr[0]
            return "G_{%s}" % argstr[0]
        if head is PrimitiveDirichletCharacters:
            return "G_{%s}^{\\text{primitive}}" % argstr[0]
        if head is GaussSum:
            assert len(args) == 2
            return "G_{" + argstr[0] + "}" + "\!\\left(" + argstr[1] + "\\right)"
        if head is StieltjesGamma:
            arg0 = args[0].latex(in_small=True)
            if len(args) == 1:
                return "\\gamma_{%s}" % arg0
            if len(args) == 2:
                return "\\gamma_{%s}\\!\\left(%s\\right)" % (arg0, argstr[1])
        if head is StirlingSeriesRemainder:
            assert len(args) == 2
            return "R_{%s}\!\\left(%s\\right)" % tuple(argstr)
        if head is FormalPowerSeries:
            assert len(args) == 2
            return "%s[[%s]]" % tuple(argstr)
        if head is FormalLaurentSeries:
            assert len(args) == 2
            return "%s(\!(%s)\!)" % tuple(argstr)
        if head is SeriesCoefficient:
            assert len(args) == 3
            return "[{%s}^{%s}] %s" % (argstr[1], argstr[2], argstr[0])
        if head is FormalGenerator:
            assert len(args) == 2
            return "%s \\text{ is the generator of } %s" % (argstr[0], argstr[1])
        if head is Parentheses:
            assert len(args) == 1
            return "\\left(" + args[0].latex() + "\\right)"
        if head is Brackets:
            assert len(args) == 1
            return "\\left[" + args[0].latex() + "\\right]"
        if head is Braces:
            assert len(args) == 1
            return "\\left\\{" + args[0].latex() + "\\right\\}"
        if head is Call:
            return argstr[0] + "\!\\left(" + ", ".join(argstr[1:]) + "\\right)"
        if head is Subscript:
            assert len(args) == 2
            return "{" + argstr[0] + "}_{" + args[1].latex(in_small=True) + "}"
        if head is Spectrum and args[0].head() is Matrix2x2:
            assert len(args) == 1
            return "\\operatorname{spec}" + argstr[0]
        if head is Det and args[0].head() is Matrix2x2:
            assert len(args) == 1
            return "\\operatorname{det}" + argstr[0]
        if head is ForAll:
            assert len(args) == 3
            return "\\text{for all } %s: %s, %s" % (argstr[0], argstr[1], argstr[2])
        if head is Exists:
            assert len(args) == 2
            return "\\text{there exists } %s: %s" % (argstr[0], argstr[1])
        if head is Cases:
            s = "\\begin{cases} "
            for arg in args:
                assert arg.head() is Tuple
                v, c = arg.args()
                #v = v.latex(in_small=True)
                v = v.latex(in_small=in_small)
                if c is Otherwise:
                    c = "\\text{otherwise}"
                else:
                    #c = c.latex(in_small=True)
                    c = c.latex(in_small=in_small)
                s += "%s, & %s\\\\" % (v, c)
            s += " \\end{cases}"
            return s
        if head is DiscreteLog:
            n, b, p = args
            n, b, p = argstr[0], b.latex(in_small=True), argstr[2]
            return "\\log_{%s}\!\\left(%s\\right) \\bmod %s" % (b, n, p)
        if head is ConreyGenerator:
            return "g_{%s}" % argstr[0]
        if head is QSeriesCoefficient:
            fun, tau, q, n, qdef = argstr
            return "[%s^{%s}] %s \; \\left(%s\\right)" % (q, n, fun, qdef)
        if head is EqualQSeriesEllipsis:
            fun, tau, q, ser, qdef = argstr
            return "%s = %s + \\ldots \; \\text{ where } %s" % (fun, ser, qdef)
        if head is Description:
            s = ""
            for arg in args:
                if arg._text is not None:
                    s += "\\text{ " + arg._text + " }"
                else:
                    s += arg.latex()
            return s
        fstr = self._args[0].latex()
        if in_small:
            spacer = ""
        else:
            spacer = "\\!"
        s = fstr + spacer + "\\left(" + ", ".join(argstr) + "\\right)"
        return s

    def _can_render_html(self):
        if self.is_integer():
            return True
        if self.head() is Decimal:
            return True
        if self.head() is Div and self.args()[0].is_integer() and self.args()[1].is_integer():
            return True
        if self.head() is Tuple:
            return all(arg._can_render_html() for arg in self.args())
        if self.head() is Set:
            return all(arg._can_render_html() for arg in self.args())
        return False

    def html(self, display=False, avoid_latex=False, single=False):
        katex = katex_function[0]
        if self.is_atom():
            if avoid_latex and self.is_integer():
                return str(self._integer)
            return katex(self.latex(), display=display)
        if self.head() is Decimal and avoid_latex:
            text = self.args()[0]._text
            if "e" in text:
                mant, expo = text.split("e")
                expo = expo.lstrip("+")
                text = mant + " &middot; 10<sup>" + expo + "</sup>"
            return text
        if self.head() is Div and avoid_latex and self.args()[0].is_integer() and self.args()[1].is_integer():
            p, q = self.args()
            return "%s/%s" % (str(self.args()[0]._integer), str(self.args()[1]._integer))
        if self.head() is Neg and avoid_latex and self.args()[0]._can_render_html():
            return "-" + self.args()[0].html(display=display, avoid_latex=True)
        if self.head() is Tuple and avoid_latex and self._can_render_html():
            return "(" + ", ".join(a.html(display=display, avoid_latex=True) for a in self.args()) + ")"
        if self.head() is Set and avoid_latex and self._can_render_html():
            return "{" + ", ".join(a.html(display=display, avoid_latex=True) for a in self.args()) + "}"
        if self.head() is Table:
            return self.html_Table()
        if self.head() is Formula:
            return katex(self._args[1].latex())
        if self.head() is References:
            return self.html_References()
        if self.head() is Assumptions:
            return self.html_Assumptions()
        if self.head() is Description:
            return self.html_Description(display=display)
        if self.head() is SymbolDefinition:
            return self.html_SymbolDefinition()
        if self.head() is Image:
            return self.html_Image(single=single)
        return katex(self.latex(), display=display)

    def html_Image(self, single=False):
        description, image = self.args()
        path = image.args()[0]._text
        s = ""
        s += """<div style="text-align:center; margin:0.6em 0.4em 0.0em 0.2em">"""
        s += """<span style="font-size:85%; color:#888">Image:</span> """
        s += description.html()

        imgid = path

        # hack: duplicated constants in html head
        thumb_size = "140px"
        full_size = "400px"

        if single and 0:
            s += """<div style="text-align:center; padding-right:1em">"""
            s += """<img id="%s", src="../../img/%s.svg" style="height:%s; margin-top:0.3em; margin-bottom:0px"/>""" % (imgid, path, full_size)
            s += """</div>"""
        else:
            s += """<button style="margin:0 0 0 0.3em" onclick="toggleBig('%s', '../../img/%s_small.svg', '../../img/%s.svg')">Big &#x1F50D;</button>""" % (imgid, path, path)
            s += """<div style="text-align:center; padding-right:1em;">"""
            s += """<img id="%s", src="../../img/%s_small.svg" style="width:%s; max-width:100%%; margin-top:0.3em; margin-bottom:0px"/>""" % (imgid, path, thumb_size)
            s += """</div>"""

        s += """</div>"""
        return s


    def html_Table(self):
        rel = self.get_arg_with_head(TableRelation)
        heads = self.get_arg_with_head(TableHeadings)
        data = self.get_arg_with_head(List)
        split = self.get_arg_with_head(TableSplit)
        colheads = self.get_arg_with_head(TableColumnHeadings)
        headrows = []
        if split is None:
            split = 1
        else:
            split = split.args()[0]._integer
        if heads is None:
            cols = len(data.args()[0].args())
        else:
            cols = len(heads.args())
        num = len(data.args())
        innum = num // split
        s = """<div style="overflow-x:auto;">"""
        s += """<table align="center" style="border:0; background-color:#fff;">"""
        s += """<tr style="border:0; background-color:#fff">"""
        j = 0
        for outer in range(split):
            s += """<td style="border:0; background-color:#fff; vertical-align:top;">"""
            s += """<table style="float: left; margin-right: 1em;">"""
            if heads is not None:
                s += "<tr>"
                for col in heads.args():
                    # the nowrap is a hack to avoid "n \ k" breaking
                    s += """<th style="white-space:nowrap;">""" + col.html(display=False, avoid_latex=True) + "</th>"
                s += "</tr>"
            if outer == split-1:
                end = num
            else:
                end = innum*(outer+1)
            for row in data.args()[innum*outer : end]:
                s += "<tr>"
                if row.head() is TableSection:
                    s += """<td colspan="%i" style="text-align:center; font-weight: bold">%s</td>""" % (cols, row.args()[0]._text)
                else:
                    if colheads is not None:
                        col = colheads.args()[j]
                        s += "<th>" + col.html(display=False, avoid_latex=True) + "</th>"
                    for i, col in enumerate(row.args()):
                        s += "<td>" + col.html(display=False, avoid_latex=True) + "</td>"
                s += "</tr>"
                j += 1
            s += """</table>"""
            s += "</td>"
        s += "</tr></table></div>"
        if rel is not None:
            s += """<div style="text-align:center; margin-top: 0.5em">"""
            s += Description("Table data:", rel.args()[0], " such that ", rel.args()[1]).html(display=True)
            s += """</div>"""
        return s

    def html_References(self):
        s = ""
        s += """<div class="entrysubhead">References:</div>"""
        s += "<ul>"
        for ref in self._args[1:]:
            s += "<li>%s</li>" % ref._text
        s += "</ul>"
        return s

    def html_Assumptions(self):
        s = ""
        #s += """<div class="entrysubhead">Assumptions:</div>"""

        #for arg in self.args():
        #    s += arg.html(display=True)
        #return s
        num = 1
        for arg in self.args():
            s += """<div style="text-align:center; margin:0.8em">"""
            if num == 1:
                strcond = "Assumptions"
            else:
                strcond = "Alternative assumptions"
            s += """<span style="font-size:85%; color:#888; margin-right:0.8em">""" + strcond + """:</span>"""
            s += arg.html(display=False)
            s += """</div>"""
            num += 1
        return s

    def html_Description(self, display=False):
        s = ""
        if display:
            s += """<div style="text-align:center; margin:0.6em">"""
        for arg in self.args():
            if arg.is_text():
                if arg._text and arg._text[0] in (",", ".", ";"):
                    s = s.rstrip()
                s += arg._text
            elif (not arg.is_atom()) and arg.head() is SourceForm:
                s += "<tt>%s</tt>" % str(arg.args()[0])
            elif (not arg.is_atom()) and arg.head() is EntryReference:
                id = arg.args()[0]._text
                s += """<a href="../../entry/%s/">%s</a>""" % (id, id)
            else:
                s += arg.html(avoid_latex=True)
            s += " "
        if display:
            s += """</div>"""
        return s

    def html_SymbolDefinition(self):
        symbol, example, description = self.args()
        s = ""
        s += """<div style="text-align:center; margin:0.6em">"""
        s += """<span style="font-size:85%; color:#888">Symbol:</span> """
        s += """<tt><a href="../../symbol/%s/">%s</a></tt>""" % (symbol._symbol, symbol._symbol)
        s += """ <span style="color:#888">&mdash;</span> """
        s += example.html()
        s += """ <span style="color:#888">&mdash;</span> """
        s += description._text
        s += """</div>"""
        return s

    def get_arg_with_head(self, head):
        for arg in self.args():
            if not arg.is_atom() and (arg.head() is head):
                return arg
        return None

    def id(self):
        id = self.get_arg_with_head(ID)
        return id._args[1]._text

    def title(self):
        title = self.get_arg_with_head(Title)
        return title._args[1]._text

    def entry_html(self, single=False, entry_dir="../../entry/", symbol_dir="../../symbol/", default_visible=False):
        id = self.id()
        all_tex = []
        image_downloads = []
        s = ""
        s += """<div class="entry">"""
        if single:
            s += """<div style="padding-top:0.4em">"""
        else:
            s += """<div style="float:left; margin-top:0.0em; margin-right:0.3em">"""
            s += """<a href="%s%s/" style="margin-left:3pt; font-size:85%%">%s</a> <span></span><br/>""" % (entry_dir, id, id)
            s += """<button style="margin-top:0.2em; margin-bottom: 0.1em;" onclick="toggleVisible('%s:info')">Details</button>""" % id
            s += """</div>"""
            s += """<div>"""

        args = self.args()
        args = [arg for arg in args if arg.head() not in (ID, Variables)]

        for arg in args:
            if arg.head() is Image:
                src = arg.get_arg_with_head(ImageSource).args()[0]._text
                image_downloads.append(src)

        # First item is always visible
        s += args[0].html(display=True, single=single)
        s += "</div>"

        # Remaining items may be hidden beneath the fold
        if single:
            s += """<div id="%s:info" style="padding: 1em; clear:both">""" % id
        else:
            if default_visible:
                s += """<div id="%s:info" style="display:visible; padding: 1em; clear:both">""" % id
            else:
                s += """<div id="%s:info" style="display:none; padding: 1em; clear:both">""" % id

        if image_downloads:
            src = image_downloads[0]
            s += """<div style="text-align:center; margin-top:0; margin-bottom:1.1em">"""
            s += """<span style="font-size:85%; color:#888">Download:</span> """
            s += """<a href="../../img/%s_small.png">png (small)</a>""" % src
            s += """ <span style="color:#888">&mdash;</span> """
            s += """<a href="../../img/%s_medium.png">png (medium)</a>""" % src
            s += """ <span style="color:#888">&mdash;</span> """
            s += """<a href="../../img/%s_large.png">png (large)</a>""" % src
            s += """ <span style="color:#888">&mdash;</span> """
            s += """<a href="../../img/%s_small.pdf">pdf (small)</a>""" % src
            s += """ <span style="color:#888">&mdash;</span> """
            s += """<a href="../../img/%s.pdf">pdf (medium/large)</a>""" % src
            s += """ <span style="color:#888">&mdash;</span> """
            s += """<a href="../../img/%s_small.svg">svg (small)</a>""" % src
            s += """ <span style="color:#888">&mdash;</span> """
            s += """<a href="../../img/%s.svg">svg (medium/large)</a>""" % src
            s += """</div>"""

        # Remaining items
        for arg in args[1:]:
            s += arg.html(display=True)
            s += "\n\n"

        # Generate TeX listing
        for arg in self.args():
            if arg.head() in (Formula, Assumptions):
                for arg2 in arg.args():
                    all_tex.append(arg2.latex())

        if all_tex:
            s += """<div class="entrysubhead">TeX:</div>"""
            s += "<pre>"
            s += "\n\n".join(all_tex)
            s += "</pre>"

        # Generate symbol table
        symbols = self.all_symbols()
        symbols = [sym for sym in symbols if sym not in exclude_symbols]
        s += """<div class="entrysubhead">Definitions:</div>"""
        s += Expr.definitions_table_html(symbols, center=True, symbol_dir=symbol_dir)

        s += """<div class="entrysubhead">Source code for this entry:</div>"""
        s += "<pre>"
        s += self.str()
        s += "</pre>"

        s += "</div></div>\n"

        return s

    @staticmethod
    def definitions_table_html(symbols, center=False, entry_dir="../../entry/", symbol_dir="../../symbol/"):
        katex = katex_function[0]
        s = ""
        if center:
            s += """<table style="margin: 0 auto">"""
        else:
            s += """<table>"""
        # s += """<tr><th>Fungrim symbol</th> <th>Notation</th> <th>Domain</th> <th>Codomain</th> <th>Description</th></tr>"""
        s += """<tr><th>Fungrim symbol</th> <th>Notation</th> <th>Short description</th></tr>"""
        for symbol in symbols:
            if symbol in descriptions:
                example, domain, codomain, description = descriptions[symbol]
                s += """<tr><td><tt><a href="%s%s/">%s</a></tt>""" % (symbol_dir, symbol.str(), symbol.str())
                s += """<td>%s</td>""" % katex(example.latex(), False)
                # domstr = ",\, ".join(dom.latex() for dom in domain)
                # s += """<td>%s</td>""" % katex(domstr, False)
                # if codomain is None:
                #     s += """<td></td>"""
                # else:
                #     s += """<td>%s</td>""" % katex(codomain.latex(), False)
                s += """<td>%s</td></tr>""" % description
        s += """</table>"""
        return s

all_builtins = []

def inject_builtin(string):
    for sym in string.split():
        globals()[sym] = Expr(symbol_name=sym)
        all_builtins.append(sym)

variable_names = set()

def inject_vars(string):
    for sym in string.split():
        e = Expr(symbol_name=sym)
        globals()[sym] = e
        variable_names.add(sym)

inject_builtin("""
True_ False_
Parentheses Brackets Braces
Ellipsis Call Subscript
Unknown Undefined
Where
Set List Tuple
SetBuilder
PowerSet
Union Intersection SetMinus Not And Or Equivalent Implies
Cardinality
Element NotElement Subset SubsetEqual
ForAll Exists
EqualAndElement
Rings CommutativeRings Fields
PP ZZ QQ RR CC HH AlgebraicNumbers
ZZGreaterEqual ZZLessEqual ZZBetween
ClosedInterval OpenInterval ClosedOpenInterval OpenClosedInterval
RealBall
UnitCircle
OpenDisk ClosedDisk BernsteinEllipse
InteriorClosure Interior
Decimal
Equal Unequal Greater GreaterEqual Less LessEqual
Pos Neg Add Sub Mul Div Mod Inv Pow
CongruentMod Odd Even
Max Min Sign Csgn Abs Floor Ceil Arg Re Im Conjugate
NearestDecimal
Minimum Maximum ArgMin ArgMax ArgMinUnique ArgMaxUnique
Solutions UniqueSolution
Supremum Infimum
Limit SequenceLimit RealLimit LeftLimit RightLimit ComplexLimit MeromorphicLimit
Derivative RealDerivative ComplexDerivative ComplexBranchDerivative MeromorphicDerivative
Sum Product
PrimeSum DivisorSum PrimeProduct DivisorProduct
Integral
IndefiniteIntegralEqual RealIndefiniteIntegralEqual ComplexIndefiniteIntegralEqual
AsymptoticTo
FormalGenerator
FormalPowerSeries FormalLaurentSeries SeriesCoefficient
HolomorphicDomain Poles BranchPoints BranchCuts EssentialSingularities Zeros UniqueZero AnalyticContinuation
ComplexZeroMultiplicity
Residue
Infinity UnsignedInfinity
Sqrt NthRoot Log LogBase Exp
Sin Cos Tan Sec Cot Csc
Asin Acos Atan Atan2 Asec Acot Acsc
Sinh Cosh Tanh Sech Coth Csch
Asinh Acosh Atanh Asech Acoth Acsch
Sinc LambertW LambertWPuiseuxCoefficient
ConstPi ConstE ConstGamma ConstI GoldenRatio
Binomial Factorial DoubleFactorial GammaFunction LogGamma DigammaFunction PolyGamma RisingFactorial FallingFactorial HarmonicNumber StirlingSeriesRemainder
Erf Erfc Erfi
UpperGamma LowerGamma
BernoulliB BernoulliPolynomial EulerE EulerPolynomial
StirlingCycle StirlingS1 StirlingS2 BellNumber
RiemannZeta RiemannZetaZero
BesselJ BesselI BesselY BesselK HankelH1 HankelH2
BesselJDerivative BesselIDerivative BesselYDerivative BesselKDerivative
CoulombF CoulombG CoulombH CoulombC CoulombSigma
Hypergeometric0F1 Hypergeometric1F1 Hypergeometric2F1 Hypergeometric2F0 Hypergeometric3F2
HypergeometricU HypergeometricUStar
Hypergeometric0F1Regularized Hypergeometric1F1Regularized Hypergeometric2F1Regularized Hypergeometric2F0Regularized Hypergeometric3F2Regularized
HypergeometricUStarRemainder
AiryAi AiryBi AiryAiPrime AiryBiPrime
LegendrePolynomial LegendrePolynomialZero GaussLegendreWeight
HermitePolynomial
ChebyshevT ChebyshevU
DedekindEta EulerQSeries DedekindEtaEpsilon DedekindSum
JacobiTheta1 JacobiTheta2 JacobiTheta3 JacobiTheta4
Divides
GCD LCM XGCD DivisorSigma MoebiusMu Totient
LegendreSymbol JacobiSymbol KroneckerSymbol
Fibonacci
PartitionsP HardyRamanujanA
KroneckerDelta
Lattice
WeierstrassP WeierstrassZeta WeierstrassSigma
PrimeNumber PrimePi
RiemannHypothesis
LogIntegral
Matrix2x2 Matrix2x1
Spectrum Det
SL2Z PSL2Z ModularGroupAction ModularGroupFundamentalDomain
ModularLambdaFundamentalDomain
ModularJ ModularLambda
PrimitiveReducedPositiveIntegralBinaryQuadraticForms
HilbertClassPolynomial
DirichletCharacter DirichletGroup PrimitiveDirichletCharacters
ConreyGenerator
DiscreteLog
Cases Otherwise
HurwitzZeta DirichletL GeneralizedBernoulliB
StieltjesGamma
DirichletLZero
GeneralizedRiemannHypothesis
DirichletLambda GaussSum JacobiSum
EisensteinG EisensteinE
EllipticK EllipticE
QSeriesCoefficient EqualQSeriesEllipsis
BetaFunction IncompleteBeta IncompleteBetaRegularized
""")


inject_builtin("""
Entry Formula ID Assumptions References Variables DomainCodomain
Description Table TableRelation TableHeadings TableColumnHeadings TableSplit TableSection
Topic Title DefinitionsTable Section Subsection SeeTopics Entries EntryReference
SourceForm SymbolDefinition
Image ImageSource
""")

# symbols we don't want to show in entry definition listings
exclude_symbols = set([Set, List, Tuple, And, Or, Implies, Equivalent, Not, Element, NotElement, Union, Intersection, SetMinus, Subset, SubsetEqual])

inject_vars("""a b c d e f g h i j k l m n o p q r s t u v w x y z""")
inject_vars("""A B C D E F G H I J K L M N O P Q R S T U V W X Y Z""")
inject_vars("""alpha beta gamma delta epsilon zeta eta theta iota kappa mu nu xi pi rho sigma tau phi chi psi omega ell""")
inject_vars("""Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa Mu Nu Xi Pi Rho Sigma Tau Phi Chi Psi Omega""")

infix_latex_table = {
    Mod: "\\bmod",
    Element: "\\in",
    NotElement: "\\notin",
    SetMinus: "\\setminus",
    Union: "\\cup",
    Intersection: "\\cap",
    Less: "<",
    LessEqual: "\\le",
    Greater: ">",
    GreaterEqual: "\\ge",
    Equal: "=",
    Unequal: "\\ne",
    Subset: "\\subset",
    SubsetEqual: "\\subseteq",
    Divides: "\\mid",
}

subscript_call_latex_table = {
    BernoulliPolynomial: "B",
    LegendrePolynomial: "P",
    ChebyshevT: "T",
    ChebyshevU: "U",
    HermitePolynomial: "H",
    HilbertClassPolynomial: "H",
    EisensteinG: "G",
    EisensteinE: "E",
    DivisorSigma: "\\sigma",
    IncompleteBeta: "\\mathrm{B}",
    IncompleteBetaRegularized: "I",
    PolyGamma: "\\psi",
}

symbol_latex_table = {
    ConstPi: "\\pi",
    ConstI: "i",
    ConstE: "e",
    ConstGamma: "\\gamma",
    GoldenRatio: "\\varphi",
    Infinity: "\\infty",
    UnsignedInfinity: "{\\tilde \\infty}",
    GammaFunction: "\\Gamma",
    LogGamma: "\\log \\Gamma",
    UpperGamma: "\\Gamma",
    Erf: "\\operatorname{erf}",
    Erfc: "\\operatorname{erfc}",
    Erfi: "\\operatorname{erfi}",
    DigammaFunction: "\\psi",
    DedekindEta: "\\eta",
    DedekindEtaEpsilon: "\\varepsilon",
    DedekindSum: "s",
    ModularJ: "j",
    ModularLambda: "\\lambda",
    JacobiTheta1: "\\theta_1",
    JacobiTheta2: "\\theta_2",
    JacobiTheta3: "\\theta_3",
    JacobiTheta4: "\\theta_4",
    WeierstrassP: "\\wp",
    WeierstrassSigma: "\\sigma",
    WeierstrassZeta: "\\zeta",
    EllipticK: "K",
    EllipticE: "E",
    EulerQSeries: "\\phi",
    PartitionsP: "p",
    MoebiusMu: "\\mu",
    HardyRamanujanA: "A",
    Sin: "\\sin",
    Sinh: "\\sinh",
    Cos: "\\cos",
    Cosh: "\\cosh",
    Tan: "\\tan",
    Tanh: "\\tanh",
    Cot: "\\cot",
    Coth: "\\coth",
    Sec: "\\sec",
    Sech: "\\sech",
    Csc: "\\csc",
    Csch: "\\csch",
    Exp: "\\exp",
    Log: "\\log",
    Atan: "\\operatorname{atan}",
    Acos: "\\operatorname{acos}",
    Asin: "\\operatorname{asin}",
    Acot: "\\operatorname{acot}",
    Atanh: "\\operatorname{atanh}",
    Acosh: "\\operatorname{acosh}",
    Asinh: "\\operatorname{asinh}",
    Acoth: "\\operatorname{acoth}",
    Atan2: "\\operatorname{atan2}",
    Sinc: "\\operatorname{sinc}",
    Hypergeometric0F1: "\\,{}_0F_1",
    Hypergeometric1F1: "\\,{}_1F_1",
    Hypergeometric2F1: "\\,{}_2F_1",
    Hypergeometric2F0: "\\,{}_2F_0",
    Hypergeometric3F2: "\\,{}_3F_2",
    HypergeometricU: "U",
    HypergeometricUStar: "U^{*}",
    Hypergeometric0F1Regularized: "\\,{}_0{\\textbf F}_1",
    Hypergeometric1F1Regularized: "\\,{}_1{\\textbf F}_1",
    Hypergeometric2F1Regularized: "\\,{}_2{\\textbf F}_1",
    Hypergeometric2F0Regularized: "\\,{}_2{\\textbf F}_0",
    Hypergeometric3F2Regularized: "\\,{}_3{\\textbf F}_2",
    AiryAi: "\\operatorname{Ai}",
    AiryBi: "\\operatorname{Bi}",
    AiryAiPrime: "\\operatorname{Ai}'",
    AiryBiPrime: "\\operatorname{Bi}'",
    LogIntegral: "\\operatorname{li}",
    GCD: "\\gcd",
    LCM: "\\operatorname{lcm}",
    XGCD: "\\operatorname{xgcd}",
    Totient: "\\varphi",
    Sign: "\\operatorname{sgn}",
    Csgn: "\\operatorname{csgn}",
    Arg: "\\arg",
    Min: "\\min",
    Max: "\\max",
    PP: "\\mathbb{P}",
    ZZ: "\\mathbb{Z}",
    QQ: "\\mathbb{Q}",
    RR: "\\mathbb{R}",
    CC: "\\mathbb{C}",
    HH: "\\mathbb{H}",
    AlgebraicNumbers: "\\overline{\\mathbb{Q}}",
    UnitCircle: "\\mathbb{T}",
    PrimePi: "\\pi",
    SL2Z: "\\operatorname{SL}_2(\\mathbb{Z})",
    PSL2Z: "\\operatorname{PSL}_2(\\mathbb{Z})",
    ModularGroupFundamentalDomain: "\\mathcal{F}",
    ModularLambdaFundamentalDomain: "\\mathcal{F}_{\\lambda}",
    PowerSet: "\\mathscr{P}",
    Ellipsis: "\\ldots",
    Spectrum: "\\operatorname{spec}",
    Det: "\\operatorname{det}",
    RiemannHypothesis: "\\operatorname{RH}",
    GeneralizedRiemannHypothesis: "\\operatorname{GRH}",
    RiemannZeta: "\\zeta",
    HurwitzZeta: "\\zeta",
    DirichletL: "L",
    DirichletLambda: "\\Lambda",
    BetaFunction: "\\mathrm{B}",
}

described_symbols = []
descriptions = {}
long_descriptions = {}
domain_tables = {}

def describe(symbol, example, domain, codomain, description):
    described_symbols.append(symbol)
    descriptions[symbol] = (example, domain, codomain, description)

def describe2(symbol, example, description, domain_table=None, long_description=None):
    described_symbols.append(symbol)
    descriptions[symbol] = (example, None, None, description)
    if long_description is not None:
        long_descriptions[symbol] = long_description
    if domain_table is not None:
        domain_tables[symbol] = domain_table



description_x_predicate = Description("The argument", SourceForm(x), "to this operator defines a locally bound variable.",
    "The corresponding predicate", P(x), "must define the domain of", x, "unambiguously; that is, it must include a statement such as",
    Element(x, S), "where", S, "is a known set.",
    "More generally,", SourceForm(x), "can be a collection of variables", Tuple(x, y, Ellipsis),
    "all of which become locally bound, with a corresponding predicate", P(x, y, Ellipsis), ".")

description_xray = Description("An X-ray plot illustrates the geometry of a complex analytic function", f(z), ".",
    "Thick black curves show where", Equal(Im(f(z)), 0), "(the function is pure real).",
    "Thick red curves show where", Equal(Re(f(z)), 0), "(the function is pure imaginary).",
    "Points where black and red curves intersect are zeros or poles.",
    "Magnitude level curves", Equal(Abs(f(z)), C), "are rendered as thin gray curves, with brighter shades corresponding to larger", C, ".",
    "Blue lines show branch cuts.",
    "The value of the function is continuous with the branch cut on the side indicated with a solid line, and discontinuous on the side indicated with a dashed line.",
    "Yellow is used to highlight important regions.")


all_entries = []
all_topics = []

def def_Topic(*args):
    topic = Topic(*args)
    all_topics.append(topic)

def make_entry(*args):
    entry = Entry(*args)
    symd = entry.get_arg_with_head(SymbolDefinition)
    if symd is not None:
        id = entry.get_arg_with_head(ID)
        symbol, example, description = symd.args()
        described_symbols.append(symbol)
        descriptions[symbol] = (example, None, None, description._text)
        domain_tables[symbol] = id.args()[0]._text
    all_entries.append(entry)

