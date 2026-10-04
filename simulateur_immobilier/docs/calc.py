"""Modeles et exemples chiffres du guide immobilier CH / FR.
Toutes les hypotheses sont des parametres : ce module sert aussi de base a l'application future.
"""
import numpy as np
from dataclasses import dataclass, field


# ---------------------------------------------------------------- utilitaires
def annuity_payment(principal, rate_annual, years, freq=12):
    r = rate_annual / freq
    n = years * freq
    if r == 0:
        return principal / n
    return principal * r / (1 - (1 + r) ** -n)


def irr(cfs, lo=-0.99, hi=1.0, tol=1e-10):
    f = lambda x: sum(c / (1 + x) ** t for t, c in enumerate(cfs))
    a, b = lo, hi
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        return float("nan")
    for _ in range(300):
        m = 0.5 * (a + b)
        fm = f(m)
        if abs(fm) < tol:
            return m
        if fa * fm < 0:
            b, fb = m, fm
        else:
            a, fa = m, fm
    return m


# ---------------------------------------------------------------- Suisse
@dataclass
class CHParams:
    P: float = 1_200_000          # prix
    f: float = 0.05               # frais d'acquisition / prix
    e_min: float = 0.20           # fonds propres minimum / valeur de nantissement
    e_hard: float = 0.10          # fonds propres durs minimum
    rank1: float = 2 / 3          # hypotheque de 1er rang
    amort_years: int = 15
    i_theo: float = 0.05          # taux theorique de tenue des charges
    m_theo: float = 0.01          # frais accessoires theoriques
    ratio_max: float = 1 / 3
    i: float = 0.018              # taux effectif (hypothese)
    m: float = 0.008              # entretien reel / an
    g: float = 0.015              # appreciation annuelle
    rent0: float = 3_200 * 12     # loyer equivalent annuel
    g_rent: float = 0.015
    r_port: float = 0.05          # rendement net du portefeuille
    tau: float = 0.38             # taux marginal revenu
    w_tax: float = 0.008          # taux marginal fortune
    vl_ratio: float = 0.65        # valeur locative / loyer de marche
    entretien_forfait: float = 0.20
    phi_fisc: float = 0.75        # valeur fiscale / valeur venale
    sell_cost: float = 0.03
    reform_year: int = 3          # annee (index) d'entree en vigueur 2029 si achat 2026
    first_buyer_ded: float = 5_000  # deduction primo-accedant annee 1 (personne seule)


def ch_affordability(p: CHParams):
    D = p.P * (1 - p.e_min)
    D2 = max(D - p.rank1 * p.P, 0)
    amort = D2 / p.amort_years
    charge = p.i_theo * D + p.m_theo * p.P + amort
    return dict(
        cash_total=p.P * (p.e_min + p.f),
        cash_hard=p.P * (p.e_hard + p.f),
        lpp_max=p.P * (p.e_min - p.e_hard),
        D=D, D1=p.rank1 * p.P, D2=D2, amort=amort,
        interest_theo=p.i_theo * D, maint_theo=p.m_theo * p.P,
        charge=charge, income_min=charge / p.ratio_max,
        k_income=(p.i_theo * (1 - p.e_min) + p.m_theo +
                  max(1 - p.e_min - p.rank1, 0) / p.amort_years) / p.ratio_max,
    )


def ch_vl_tax(V_market, D, interest, p: CHParams, year_idx):
    """Surplus d'impot sur le revenu (proprietaire vs locataire) et effet fortune."""
    rent_mkt = p.rent0 * (1 + p.g_rent) ** year_idx
    if year_idx < p.reform_year:
        vl = p.vl_ratio * rent_mkt
        taxable = vl - interest - p.entretien_forfait * vl
        inc_tax = p.tau * taxable
    else:
        k = year_idx - p.reform_year  # annees depuis reforme
        ded = max(p.first_buyer_ded * (1 - 0.1 * k), 0)
        inc_tax = -p.tau * min(ded, interest)
    wealth_base = p.phi_fisc * V_market - D
    return inc_tax, wealth_base * p.w_tax


def ch_buy_vs_rent(p: CHParams, years=25):
    """Patrimoine net acheteur vs locataire qui investit la difference de flux."""
    a = ch_affordability(p)
    cash0 = a["cash_total"]
    D = a["D"]
    port_rent = cash0          # le locataire place l'apport
    port_buy = 0.0
    V = p.P
    out = []
    for t in range(years):
        interest = p.i * D
        amort = a["amort"] if t < p.amort_years else 0.0
        inc_tax, w_buy = ch_vl_tax(V, D, interest, p, t)
        rent = p.rent0 * (1 + p.g_rent) ** t
        cost_buy = interest + amort + p.m * V + inc_tax + w_buy
        cost_rent = rent + p.w_tax * port_rent * 1.0
        # celui qui paie le moins investit la difference
        diff = cost_buy - cost_rent
        port_rent = port_rent * (1 + p.r_port) + max(diff, 0)
        port_buy = port_buy * (1 + p.r_port) + max(-diff, 0)
        V *= 1 + p.g
        D -= amort
        hold = t + 1
        gain = V - p.P * (1 + p.f)
        ibgi_rate = gibgi_rate(hold)
        net_sale = V * (1 - p.sell_cost) - D - max(gain, 0) * ibgi_rate
        out.append((hold, net_sale + port_buy, port_rent))
    return np.array(out)


def gibgi_rate(h):
    if h < 2: return 0.50
    if h < 4: return 0.40
    if h < 6: return 0.30
    if h < 8: return 0.20
    if h < 10: return 0.15
    if h < 25: return 0.10
    return 0.02


def time_to_equity(E0, S_month, r, P0, g, need_ratio, Y=None, k_income=None, gY=0.02, Tmax=30):
    """Annees pour que l'epargne investie couvre need_ratio * P(T)."""
    E = E0
    for m in range(Tmax * 12 + 1):
        T = m / 12
        PT = P0 * (1 + g) ** T
        ok_e = E >= need_ratio * PT
        ok_y = True if Y is None else Y * (1 + gY) ** T >= k_income * PT
        if ok_e and ok_y:
            return T
        E = E * (1 + r) ** (1 / 12) + S_month
    return float("nan")


# ---------------------------------------------------------------- France
@dataclass
class FRParams:
    P: float = 250_000
    notaire: float = 0.08
    meubles: float = 5_000
    frais_bancaires: float = 0.015  # garantie + dossier / montant emprunte
    ltv: float = 0.80
    i: float = 0.034
    years: int = 20
    ins: float = 0.0025          # assurance emprunteur / capital initial
    rent_m: float = 1_000        # loyer meuble mensuel
    occ: float = 11 / 12
    tf: float = 1_100            # taxe fonciere
    copro: float = 700           # charges non recuperables
    pno: float = 150
    gestion: float = 0.08        # gestion agence (sur loyers encaisses)
    entretien: float = 800
    compta: float = 450          # expert-comptable LMNP reel
    cfe: float = 300
    land: float = 0.15           # quote-part terrain non amortissable
    amort_bat_years: int = 30
    amort_meubles_years: int = 7
    g: float = 0.015
    g_rent: float = 0.015
    tau_ir: float = 0.20         # taux minimum non-resident
    ps: float = 0.075            # prelevement de solidarite (affilie CH)
    hold: int = 15


def fr_cashflows(p: FRParams, regime="micro"):
    loan = p.ltv * p.P
    cash0 = p.P * (1 - p.ltv) + p.P * p.notaire + p.meubles + p.frais_bancaires * loan
    pay = annuity_payment(loan, p.i, p.years) * 12
    bal = loan
    base_amort = (1 - p.land) * (p.P * (1 + p.notaire)) / p.amort_bat_years
    amort_m = p.meubles / p.amort_meubles_years
    cum_amort = 0.0
    deficit_carry = 0.0
    rows = []
    for t in range(p.hold):
        rent = p.rent_m * 12 * p.occ * (1 + p.g_rent) ** t
        interest = 0.0
        principal = 0.0
        for _ in range(12):
            it = bal * p.i / 12
            pr = pay / 12 - it
            interest += it
            principal += pr
            bal -= pr
        ins = p.ins * loan
        charges = p.tf + p.copro + p.pno + p.gestion * rent + p.entretien + p.cfe
        if regime == "reel":
            charges += p.compta
        cf_pre_tax = rent - charges - pay - ins
        if regime == "micro":
            taxable = 0.5 * rent
        else:
            res_before_amort = rent - charges - interest - ins
            am = base_amort + (amort_m if t < p.amort_meubles_years else 0)
            # l'amortissement ne peut pas creer de deficit (il est reporte)
            usable = min(am, max(res_before_amort, 0))
            cum_amort += usable
            res = res_before_amort - usable
            res += deficit_carry
            deficit_carry = min(res, 0)
            taxable = max(res, 0)
        tax = taxable * (p.tau_ir + p.ps)
        rows.append(dict(t=t + 1, rent=rent, charges=charges, interest=interest, principal=principal,
                         ins=ins, pay=pay, cf_pre_tax=cf_pre_tax, taxable=taxable, tax=tax,
                         cf=cf_pre_tax - tax, bal=bal))
    V = p.P * (1 + p.g) ** p.hold
    pv_tax, pv_detail = fr_pv_tax(p, V, cum_amort if regime == "reel" else 0.0)
    sale_net = V - bal - pv_tax
    cfs = [-cash0] + [r["cf"] for r in rows]
    cfs[-1] += sale_net
    return dict(rows=rows, cash0=cash0, loan=loan, pay=pay, V=V, bal=bal, pv_tax=pv_tax,
                pv_detail=pv_detail, sale_net=sale_net, irr=irr(cfs), cum_amort=cum_amort)


def fr_pv_tax(p: FRParams, V, amort_reint):
    h = p.hold
    acq = p.P + 0.075 * p.P + (0.15 * p.P if h > 5 else 0)  # forfaits frais 7,5 % et travaux 15 %
    acq -= amort_reint
    gain = max(V - acq, 0)
    yrs = max(h - 5, 0)
    ab_ir = min(0.06 * min(yrs, 16) + (0.04 if h >= 22 else 0), 1.0)
    ab_ps = min(0.0165 * min(yrs, 16) + (0.016 if h >= 22 else 0) + 0.09 * max(h - 22, 0), 1.0)
    ir = gain * (1 - ab_ir) * 0.19
    ps = gain * (1 - ab_ps) * p.ps
    return ir + ps, dict(acq=acq, gain=gain, ab_ir=ab_ir, ab_ps=ab_ps, ir=ir, ps=ps)


if __name__ == "__main__":
    p = CHParams()
    a = ch_affordability(p)
    for k, v in a.items():
        print(f"{k:15s} {v:,.3f}")
    res = ch_buy_vs_rent(p)
    for h, b, r in res[[0, 4, 9, 14, 19, 24]]:
        print(f"h={h:.0f} buy={b:,.0f} rent={r:,.0f} diff={b - r:,.0f}")
    print("time to equity", time_to_equity(150_000, 4_000, 0.05, 1_200_000, 0.015, 0.25))
    for reg in ("micro", "reel"):
        fr = fr_cashflows(FRParams(), reg)
        r0 = fr["rows"][0]
        print(reg, "cash0", round(fr["cash0"]), "pay", round(fr["pay"]), "cf1", round(r0["cf"]),
              "tax1", round(r0["tax"]), "V", round(fr["V"]), "bal", round(fr["bal"]),
              "pvtax", round(fr["pv_tax"]), "irr", round(fr["irr"], 4), "amort", round(fr["cum_amort"]))
        print("  pv", {k: round(v, 3) for k, v in fr["pv_detail"].items()})
