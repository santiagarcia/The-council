"""Build corpus_campaign/material_data/d21_council_constants.jsonl (Curie, D-21).

Reads source text from discovery_cache to quote the line that reads each PROPS(i),
computes validity checks (positive-definite elasticity, nu < 0.5, activation estimates),
and writes one row per source.  Values are fixed here BEFORE any comparison (D-21 cond. 1).
"""
import json, math, re, hashlib
from pathlib import Path
import numpy as np

ROOT = Path('/home/ammslab3/softwarex_work')
CACHE = ROOT / 'discovery_cache'
OUT = ROOT / 'corpus_campaign/material_data/d21_council_constants.jsonl'
HARVEST = {json.loads(l)['source_id']: json.loads(l)
           for l in open(ROOT / 'corpus_campaign/material_data/d19_harvest.jsonl')}
REG = {r['source_id']: r for r in json.load(open(ROOT / 'final-umat/paper_results/corpus/corpus_registry.json'))['records']}
FAM = {r['source_id']: r['family'] for r in json.load(open(ROOT / 'corpus_run/material_families_checked_E.json'))['rows']}

R_GAS = 8314.4598484848  # mJ/(mol K), as hard-coded in the Leonov sources


def quote_props(src, idx, expr=None):
    """Return 'path:line: text' of the first executable line reading PROPS(idx) (or expr)."""
    lines = (CACHE / src).read_text(errors='replace').splitlines()
    if expr is None:
        pat = re.compile(r'props\s*\(\s*%d\s*\)' % idx, re.I)
    else:
        pat = re.compile(re.escape(expr), re.I)
    for n, t in enumerate(lines, 1):
        s = t.strip()
        if not s or s.startswith('!') or (not src.endswith('.f90') and t[:1] in 'cC*'):
            continue
        if pat.search(t):
            return f"{src}:{n}: {s}"
    raise SystemExit(f"no PROPS({idx}) line found in {src} (expr={expr})")


def iso_C(E, nu):
    lam = E * nu / ((1 + nu) * (1 - 2 * nu)); mu = E / (2 * (1 + nu))
    C = np.zeros((6, 6)); C[:3, :3] = lam
    for i in range(3): C[i, i] += 2 * mu
    for i in range(3, 6): C[i, i] = mu
    return C


def ortho_S(E1, E2, E3, n12, n13, n23, G12, G13, G23):
    S = np.zeros((6, 6))
    S[0, 0], S[1, 1], S[2, 2] = 1 / E1, 1 / E2, 1 / E3
    S[0, 1] = S[1, 0] = -n12 / E1
    S[0, 2] = S[2, 0] = -n13 / E1
    S[1, 2] = S[2, 1] = -n23 / E2
    S[3, 3], S[4, 4], S[5, 5] = 1 / G12, 1 / G13, 1 / G23
    return S


def pd(M):
    ev = np.linalg.eigvalsh(0.5 * (M + M.T))
    return bool(ev.min() > 0), float(ev.min())


def c(index, name, value, unit, basis, confidence):
    assert confidence in ('chosen', 'class-typical', 'looked-up', 'author-kept', 'author-other-context', 'interpreted')
    assert 'as recalled' not in basis, basis  # R-4
    return dict(index=index, name=name, value=value, unit=unit, basis=basis, confidence=confidence)


ROWS = []


def row(source_id, *, material_class, class_basis, unit_system, props_map, sets, nstatv, nstatv_basis,
        initial_statev, cmname_switch=None, reads_temp=False, reads_temp_note='', reads_coords_or_noel=False,
        coords_note='', status='covered', experiment_origin='council_deck', flags=(), lookups=(), notes='',
        family=None, celent=None, formulation_3d_only=None, kinc1_statev_reset=None, licence_hold=None,
        duplicate_of=None, counts_in_tier=True, static_scan_overrides=(), undefined_outputs=()):
    h = HARVEST.get(source_id)
    reg = REG[source_id]
    # every PROPS index read by the code must be set in every set, and only those
    idxs = sorted(p['index'] for p in props_map)
    for s in sets:
        got = sorted(k['index'] for k in s['constants'])
        assert got == idxs, (source_id, s['set_id'], set(idxs) ^ set(got))
    assert len(sets) >= 2, source_id
    ROWS.append(dict(
        schema='d21_council_constants/1',
        source_id=source_id,
        harvest_key=h['key'] if h else None,
        harvest_status=h['status'] if h else None,
        registry_terminal_state=reg['terminal_state'],
        registry_compiled=reg['compiled'],
        family=family or FAM.get(source_id) or (h['family'] if h else None),
        repository=reg['repository'], commit=reg['commit'], license_spdx=reg['license_spdx'],
        material_data_origin='council_chosen',
        experiment_origin=experiment_origin,
        status=status,
        material_class=material_class, class_basis=class_basis,
        unit_system=unit_system,
        props_map=props_map,
        nstatv=nstatv, nstatv_basis=nstatv_basis, initial_statev=initial_statev,
        cmname_switch=cmname_switch,
        reads_temp=reads_temp, reads_temp_note=reads_temp_note,
        reads_coords_or_noel=reads_coords_or_noel, coords_note=coords_note,
        sets=sets, flags=list(flags), lookups=list(lookups), notes=notes,
        celent=celent, formulation_3d_only=formulation_3d_only, kinc1_statev_reset=kinc1_statev_reset,
        licence_hold=licence_hold, duplicate_of=duplicate_of, counts_in_tier=counts_in_tier,
        static_scan_overrides=list(static_scan_overrides), undefined_outputs=list(undefined_outputs),
        amendment_ref=['corpus_campaign/material_data/d21_rule_amendment_1.json', 'corpus_campaign/material_data/d21_rule_amendment_2.json'],
        selection_rule_ref='corpus_campaign/material_data/d21_selection_rule.json',
        chosen_by='Curie', chosen_on='2026-10-02', vera_accepted_template=False, vera_accepted_instance=False,
    ))


def pmap(src, spec):
    """spec: list of (index, name[, expr])"""
    out = []
    for item in spec:
        i, name = item[0], item[1]
        expr = item[2] if len(item) > 2 else None
        out.append(dict(index=i, name=name, code=quote_props(src, i, expr)))
    return out


def iso_set(set_id, label, material, E, nu, unit, basis_E, basis_nu, conf, independence, extra=(), idx=(1, 2)):
    okpd, emin = pd(iso_C(E, nu))
    cs = [c(idx[0], 'E', E, unit, basis_E, conf), c(idx[1], 'nu', nu, '-', basis_nu, conf)] + list(extra)
    return dict(set_id=set_id, label=label, material=material, independence=independence, constants=cs,
                validity=dict(positive_definite=okpd, min_eig_C=emin, nu_lt_half=nu < 0.5),
                activation='elastic source: no threshold; informativeness is the elastic-response gate')


# ---------------------------------------------------------------- elasticity, isotropic
STEEL = ('structural steel', 210000.0, 0.30)
ALU = ('aluminium alloy (6061-T6 class)', 70000.0, 0.33)
for src, cls in [
    ('BAMresearch__fenics-constitutive/examples/umat/src/umat_linear_elastic.f', 'isotropic linear elastic metal (generic: no class named in code or repo example)'),
    ('calculix__ccx_fff/src/umat.f', 'isotropic linear elastic metal (generic: CalculiX example routine names no material)'),
]:
    pm = pmap(src, [(1, 'E'), (2, 'nu')])
    sets = [iso_set('A', 'steel', STEEL[0], STEEL[1], STEEL[2], 'MPa', 'handbook E of structural steel', 'handbook nu of steel', 'class-typical', 'base set'),
            iso_set('B', 'aluminium', ALU[0], ALU[1], ALU[2], 'MPa', 'handbook E of Al alloys', 'handbook nu of Al alloys', 'class-typical', 'different material of the same class (E -67%, nu +10%)')]
    row(src, material_class=cls, class_basis='code comment "ELASTIC USER SUBROUTINE"/"EXAMPLE LINEAR ELASTIC MATERIAL"; no material named',
        formulation_3d_only='hard-codes 6 stress/DDSDDE components (DDSDDE(4..6,4..6), stress(1..6)): run on 3D continuum elements (NTENS=6) only',
        unit_system='MPa (any consistent set; the routine is unit-free)', props_map=pm, sets=sets, nstatv=0,
        nstatv_basis='routine never indexes STATEV', initial_statev=None)

src = 'compas-dev__compas_fea2/data/umat/umat-hooke-iso.f'
pm = pmap(src, [(1, 'E'), (2, 'nu')])
sets = [iso_set('A', 'steel', STEEL[0], STEEL[1], STEEL[2], 'MPa', 'handbook E of structural steel', 'handbook nu of steel', 'class-typical', 'base set'),
        iso_set('B', 'concrete C30/37', 'normal-weight normal-strength concrete (C30/37 class), uncracked', 33000.0, 0.20, 'MPa', 'handbook E of normal-strength concrete (uncited)', 'handbook nu of uncracked concrete (uncited)', 'class-typical', 'different structural material (E -84%, nu -33%)')]
row(src, material_class='isotropic linear elastic structural material (compas_fea2 is a structural-engineering FE front end)',
    class_basis='repository purpose (structural engineering); German comments E-Modul/Querkontraktionszahl', unit_system='MPa',
    props_map=pm, sets=sets, nstatv=0, nstatv_basis='routine never indexes STATEV', initial_statev=None,
    formulation_3d_only='hard-codes stress(4:6) and ddsdde(4..6): NTENS=6 only',
    flags=['DDSDDE off-diagonal shear entries are never zeroed by the routine (relies on Abaqus zero-initialising DDSDDE); not a data issue'])

src = 'CriticalSoilModels__incremental-driver/src/elastic.f90'
pm = pmap(src, [(1, 'E'), (2, 'nu')])
sets = [iso_set('A', 'dense sand', 'dense sand, drained', 50000.0, 0.25, 'kPa', 'typical drained Young modulus of dense sand', 'typical drained nu of sand', 'class-typical', 'base set'),
        iso_set('B', 'soft clay', 'soft clay, drained', 5000.0, 0.35, 'kPa', 'typical drained Young modulus of soft clay', 'typical drained nu of clay', 'class-typical', 'different soil of the same class (E -90%, nu +40%)')]
row(src, material_class='soil (repository CriticalSoilModels / incremental driver for soil models)', class_basis='repository name and purpose',
    unit_system='kPa (geotechnical convention; routine is unit-free)', props_map=pm, sets=sets, nstatv=0,
    nstatv_basis='routine never indexes STATEV (argument named NSTATEV)', initial_statev=None,
    status='covered_blocked_non_data', formulation_3d_only='hard-codes DDSDDE(4..6,4..6): NTENS=6 only',
    flags=['registry compiled=False: needs Fortran module stdlib_kinds (missing helper, not data)'])

# ---------------------------------------------------------------- Christensen (elastic + failure index)
src = 'CLD-Rostock__Christensen_FailureIndex/Subroutine/christensen_subroutine.for'
pm = pmap(src, [(1, 'E'), (2, 'nu'), (3, 'T'), (4, 'C')])
A = iso_set('A', 'brittle polymer, author T/C', 'PMMA-class brittle isotropic polymer', 3000.0, 0.35, 'MPa', 'typical E of PMMA', 'typical nu of PMMA', 'class-typical', 'base set; T/C = 1/3 < 0.5 exercises the fracture-criterion branch',
            extra=[c(3, 'T', 100.0, 'MPa', "README usage example of the author's Python class (README.md:140 'Christensen_class(stress_tensor, T=100, C=300)'): another context, not this routine", 'author-other-context'),
                   c(4, 'C', 300.0, 'MPa', "README usage example (README.md:140 'C=300')", 'author-other-context')])
B = iso_set('B', 'ductile metal, T=C', 'aluminium-alloy-class isotropic metal', 70000.0, 0.33, 'MPa', 'handbook E of Al alloys', 'handbook nu of Al alloys', 'class-typical', 'different class member; T/C = 1 exercises the invariant-only branch (AUX_B = 0)',
            extra=[c(3, 'T', 250.0, 'MPa', 'typical 6061-T6 yield/strength level, symmetric', 'class-typical'),
                   c(4, 'C', 250.0, 'MPa', 'T=C chosen to select the T/C >= 0.5 branch', 'chosen')])
row(src, material_class='isotropic material assessed with the Christensen failure criterion', class_basis='README (failure criterion for isotropic materials, Python defaults T=100, C=300)',
    unit_system='MPa', props_map=pm, sets=[A, B], nstatv=2, nstatv_basis='STATEV(1)=UTIL, STATEV(2)=FN (christensen_subroutine.for:196-197)',
    initial_statev='0 (STATEV only written)',
    formulation_3d_only='hard-codes DDSDDE(4..6,4..6) and SPRINC on 3 direct + 3 shear components: NTENS=6 only',
    undefined_outputs=[dict(output='STATEV(2) (FN)', kind='nan_in_original', when='exactly zero stress: RHO_FAIL=RHO/UTIL=0/0', ruling='D-21a (d): listed, never compared')],
    flags=['D-21a (d): STATEV(1:2) are write-only (never read) -> classed "elastic with output state"; needs the static + dynamic write-only proof on the pass'])

# ---------------------------------------------------------------- matmodlab thermoelastic (reads TEMP)
src = 'matmodlab__matmodlab2/matmodlab2/umat/umats/umat_thermoelastic.f90'
pm = pmap(src, [(1, 'E(T0)'), (2, 'NU(T0)'), (3, 'T0'), (4, 'E(T1)'), (5, 'NU(T1)'), (6, 'T1'), (7, 'ALPHA'), (8, 'T_INITIAL')])
def thermo(set_id, label, mat, E0, n0, T0, E1, n1, T1, al, Ti, indep, conf_note):
    cs = [c(1, 'E(T0)', E0, 'MPa', f'{mat} modulus at room temperature', 'class-typical'),
          c(2, 'NU(T0)', n0, '-', f'{mat} nu at room temperature', 'class-typical'),
          c(3, 'T0', T0, 'K', 'room temperature', 'chosen'),
          c(4, 'E(T1)', E1, 'MPa', f'{mat} modulus at T1 ({conf_note})', 'class-typical'),
          c(5, 'NU(T1)', n1, '-', f'{mat} nu at T1', 'chosen'),
          c(6, 'T1', T1, 'K', 'upper end of the interpolation range', 'chosen'),
          c(7, 'ALPHA', al, '1/K', f'{mat} linear thermal expansion', 'class-typical'),
          c(8, 'T_INITIAL', Ti, 'K', 'reference (stress-free) temperature = T0', 'chosen')]
    v = all(pd(iso_C(E, n))[0] for E, n in ((E0, n0), (E1, n1)))
    return dict(set_id=set_id, label=label, material=mat, independence=indep, constants=cs,
                non_props_choices=[dict(input='TEMP field', value='TEMP = 293 K at start, linear ramp to 493 K over the step (DTEMP>0 every increment)',
                                        basis='D-21 cond. 5: temperature council-chosen; ramp keeps FAC1 inside (0,1) so the moduli actually vary', confidence='chosen')],
                validity=dict(positive_definite_at_T0_and_T1=v, nu_lt_half=max(n0, n1) < 0.5, T1_gt_T0=T1 > T0),
                activation='thermoelastic: modulus interpolation active for T in (T0,T1); thermal strain ALPHA*(T-T_INITIAL) nonzero once T>293')
sets = [thermo('A', 'steel', 'carbon steel', 200000.0, 0.30, 293.0, 160000.0, 0.32, 873.0, 1.2e-5, 293.0, 'base set', '~20% drop to 600 C'),
        thermo('B', 'aluminium', 'aluminium alloy', 70000.0, 0.33, 293.0, 50000.0, 0.35, 623.0, 2.3e-5, 293.0, 'different material of the same class; alpha +92%, E slope different', '~30% drop to 350 C')]
row(src, material_class='isotropic thermoelastic metal (generic; no class named)', class_basis='code comment "ISOTROPIC THERMO-ELASTICITY WITH LINEARLY VARYING MODULI"',
    unit_system='MPa, K', props_map=pm, sets=sets, nstatv=12, nstatv_basis="code requires exactly 12: 'IF (NSTATV /= 12) ... STDB_ABQERR(-3,...)' (umat_thermoelastic.f90:34)",
    initial_statev='0 (STATEV only written)', reads_temp=True,
    reads_temp_note='genuine: FAC1=(TEMP-PROPS(3))/(PROPS(6)-PROPS(3)) at :52 and thermal strain at :91. Under D-19a R2 refused (needs_documented_temperature) until G5 (temperature on displacement elements) lands; D-21 cond. 5 lets the council choose the temperature, recorded per set.',
    status='covered_blocked_non_data', flags=['blocked until harness package G5 (temperature on displacement elements); not data', 'NSTATV must be 12 or the original calls STDB_ABQERR(-3) (error branch, D-21 cond. 4)'])

# ---------------------------------------------------------------- compas transversely isotropic (stiffness inputs)
src = 'compas-dev__compas_fea2/data/umat/umat-hooke-transversaliso.f'
pm = pmap(src, [(1, 'c1111'), (2, 'c2222'), (3, 'c1122'), (4, 'c2233'), (5, 'c1212')])
def ti_from_eng(E1, E2, n12, n23, G12):
    G23 = E2 / (2 * (1 + n23))
    S = ortho_S(E1, E2, E2, n12, n12, n23, G12, G12, G23)
    C = np.linalg.inv(S)
    return C, S, G23
def ti_set(set_id, label, mat, E1, E2, n12, n23, G12, indep):
    C, S, G23 = ti_from_eng(E1, E2, n12, n23, G12)
    vals = dict(c1111=C[0, 0], c2222=C[1, 1], c1122=C[0, 1], c2233=C[1, 2], c1212=C[3, 3])
    basis = f'computed from {mat} engineering constants E1={E1}, E2=E3={E2}, nu12=nu13={n12}, nu23={n23}, G12=G13={G12} MPa (G23=E2/(2(1+nu23))={G23:.1f}); C=inv(S)'
    cs = [c(i + 1, k, round(float(v), 3), 'MPa', basis, 'class-typical') for i, (k, v) in enumerate(vals.items())]
    # code's own matrix
    Cc = np.zeros((6, 6)); a = [x['value'] for x in cs]
    c1111, c2222, c1122, c2233, c1212 = a; c2323 = 0.5 * (c2222 - c2233)
    Cc[0, :3] = [c1111, c1122, c1122]; Cc[1, :3] = [c1122, c2222, c2233]; Cc[2, :3] = [c1122, c2233, c2222]
    Cc[3, 3] = Cc[4, 4] = c1212; Cc[5, 5] = c2323
    ok, emin = pd(Cc)
    return dict(set_id=set_id, label=label, material=mat, independence=indep, constants=cs,
                validity=dict(positive_definite_code_matrix=ok, min_eig_C=emin, engineering=dict(E1=E1, E2=E2, nu12=n12, nu23=n23, G12=G12, G23=round(G23, 3))),
                activation='elastic source: no threshold')
sets = [ti_set('A', 'CFRP UD', 'T300/epoxy-class unidirectional CFRP (fibre along 1)', 135000.0, 10000.0, 0.30, 0.45, 5000.0, 'base set'),
        ti_set('B', 'GFRP UD', 'E-glass/epoxy-class unidirectional GFRP (fibre along 1)', 40000.0, 10000.0, 0.28, 0.40, 4000.0, 'different material of the same class (E1 -70%, G12 -20%)')]
row(src, material_class='transversely isotropic linear elastic solid, axis 1 = symmetry axis', class_basis='file name "hooke-transversaliso"; c2323=(c2222-c2233)/2 in code fixes 2-3 as isotropy plane; UD fibre composite chosen as the representative class',
    unit_system='MPa', props_map=pm, sets=sets, nstatv=0, nstatv_basis='routine never indexes STATEV', initial_statev=None,
    formulation_3d_only='ddsdde(1..6,1:6) and stress(i), i=1..6, hard-coded: NTENS=6 only')

# ---------------------------------------------------------------- Mohr-Coulomb (baw-de)
src = 'baw-de__poroMechanicalFoam/abaqusUMATs/abaqusUmatMohrCoulomb/MohrCoulombAbaqus.for'
pm = pmap(src, [(1, 'E'), (2, 'nu'), (3, 'cohesion'), (4, 'phi (deg)'), (5, 'psi (deg)')])
def mc_set(set_id, label, mat, E, nu, coh, phi, psi, indep, confs):
    k = (1 + math.sin(math.radians(phi))) / (1 - math.sin(math.radians(phi)))
    sc = 2 * coh * math.sqrt(k)
    cs = [c(1, 'E', E, 'kPa', f'{mat}: typical drained Young modulus', confs),
          c(2, 'nu', nu, '-', f'{mat}: typical drained nu', confs),
          c(3, 'c', coh, 'kPa', f'{mat}: typical effective cohesion', confs),
          c(4, 'phi', phi, 'deg', f'{mat}: typical effective friction angle', confs),
          c(5, 'psi', psi, 'deg', "small dilatancy, 0 < psi <= phi (R-1: source header ':15 dilation angle, psi [degrees] Cannot be set to zero')", 'chosen')]
    return dict(set_id=set_id, label=label, material=mat, independence=indep, constants=cs,
                validity=dict(positive_definite=pd(iso_C(E, nu))[0], nu_lt_half=nu < 0.5, psi_le_phi=psi <= phi, phi_gt_0=phi > 0, psi_gt_0=psi > 0),
                activation=f'uniaxial compressive strength 2c*sqrt(k) = {sc:.1f} kPa -> yield strain ~ {sc / E:.2e} (< 0.5*ceiling 0.01); tension apex c/tan(phi) = {coh / math.tan(math.radians(phi)):.1f} kPa')
sets = [mc_set('A', 'medium dense sand', 'medium dense sand (drained)', 30000.0, 0.30, 5.0, 32.0, 2.0, 'base set', 'class-typical'),
        mc_set('B', 'stiff clay', 'stiff overconsolidated clay (drained)', 10000.0, 0.35, 15.0, 24.0, 3.0, 'different soil of the same class (E -67%, c x3, phi -25%)', 'class-typical')]
row(src, material_class='drained soil (Mohr-Coulomb, poroMechanicalFoam geotechnics)', class_basis='code comments "c - cohesion", "phi angle of friction (degrees)"; repository is geotechnical (BAW)',
    unit_system='kPa, degrees', props_map=pm, sets=sets, nstatv=1, nstatv_basis="only STATEV(1)=real(region) written (MohrCoulombAbaqus.for:236)",
    initial_statev='0 (not read)', reads_temp=False,
    reads_temp_note="harvest flag reads_temp=True is a static-scan false positive: TEMP is only declared (:127 is the TEMP dummy-argument declaration), never used",
    reads_coords_or_noel=False, coords_note="NOEL appears only in a KINC=1/NOEL=1/NPT=1 banner WRITE (:194); no effect on STRESS/DDSDDE",
    kinc1_statev_reset='none (the KINC==1 block at :194 only writes a banner)',
    static_scan_overrides=[dict(flag='reads_temp', proposed=False, static_evidence='TEMP occurs only in the argument list and declarations (:3, :127); no executable use', dynamic_evidence='to be produced on the pass: identical STRESS/DDSDDE/STATEV with TEMP=0 and TEMP=500', status='proposed, needs Vera per D-21a (e)')])

# ---------------------------------------------------------------- HFE bone (2 forks)
for src, e0 in [('artorg-unibe-ch__HFE/02_CODE/abq/UMAT_BIPHASIC.f', '10490'), ('simoneponcioni__HFE/02_CODE/abq/UMAT_BIPHASIC.f', '8632')]:
    pm = pmap(src, [(1, 'BVTVC'), (2, 'BVTVT'), (3, 'PBVC'), (4, 'PBVT'), (5, 'MM1'), (6, 'MM2'), (7, 'MM3')])
    A = dict(set_id='A', label='trabecular', material='human trabecular bone, single trabecular phase (PBVT=1, PBVC=0)', independence='base set; trabecular branch (PBVT>0, PBVC=0)',
             constants=[c(1, 'BVTVC', 0.0, '-', 'no cortical phase', 'chosen'), c(2, 'BVTVT', 0.25, '-', 'typical trabecular BV/TV (femoral/radial 0.1-0.35)', 'class-typical'),
                        c(3, 'PBVC', 0.0, '-', 'no cortical phase', 'chosen'), c(4, 'PBVT', 1.0, '-', 'element fully trabecular', 'chosen'),
                        c(5, 'MM1', 0.85, '-', 'fabric eigenvalue, typical trabecular anisotropy, m1+m2+m3=3', 'class-typical'),
                        c(6, 'MM2', 0.95, '-', 'fabric eigenvalue', 'class-typical'), c(7, 'MM3', 1.20, '-', 'fabric eigenvalue (main direction)', 'class-typical')],
             validity=dict(single_phase=True, fabric_trace=3.0, hardcoded_E0_MPa=e0),
             activation='E ~ E0*BVTV^KS ~ 1.2 GPa, yield ~ SIGD0P*BVTV^PP ~ 4.7 MPa -> yield strain ~ 0.4% (< 0.5*ceiling)')
    B = dict(set_id='B', label='cortical', material='human cortical bone, single cortical phase (PBVC=1, PBVT=0)', independence='different material of the same class; cortical branch',
             constants=[c(1, 'BVTVC', 0.90, '-', 'typical cortical BV/TV (porosity ~10%)', 'class-typical'), c(2, 'BVTVT', 0.0, '-', 'no trabecular phase', 'chosen'),
                        c(3, 'PBVC', 1.0, '-', 'element fully cortical', 'chosen'), c(4, 'PBVT', 0.0, '-', 'no trabecular phase', 'chosen'),
                        c(5, 'MM1', 0.95, '-', 'near-isotropic fabric, trace 3', 'chosen'), c(6, 'MM2', 1.00, '-', 'near-isotropic fabric', 'chosen'), c(7, 'MM3', 1.05, '-', 'near-isotropic fabric', 'chosen')],
             validity=dict(single_phase=True, fabric_trace=3.0),
             activation='E ~ 15992*0.9 ~ 14.4 GPa, SIGD0P*BVTV ~ 64 MPa -> yield strain ~ 0.45%')
    row(src, material_class='bone (cortical/trabecular), fabric-based elasto-viscoplastic damage', class_basis='header "MATERIAL CONSTANTS FOR BONE"; E0, V0, strengths hard-coded; PROPS are density and fabric',
        unit_system='MPa (hard-coded constants); PROPS dimensionless', props_map=pm, sets=[A, B], nstatv=31,
        nstatv_basis='highest index written STATEV(31)=DFGRD1(3,3) (UMAT_BIPHASIC.f:1074); header comment says *DEPVAR 18, which would overrun',
        initial_statev='code zeroes STATEV(1:18) at KSTEP=1,KINC=1; 19-31 written before read',
        kinc1_statev_reset="IF (KSTEP.EQ.(1).AND.KINC .EQ.(1)) THEN ... STATEV(K1)=0, K1=1..18",
        reads_coords_or_noel=False, coords_note='NOEL only in diagnostic WRITE statements',
        status='covered_blocked_non_data', flags=['registry compiled=False for this source: compile problem, not data; constants are ready once it compiles',
                                                  'mixed elements (PBVC>0 and PBVT>0) leave E0=V0=MU0=0 (no branch) -> singular; both sets are single-phase by rule',
                                                  'forks differ in hard-coded trabecular E0 (10490 vs 8632): treated as different sources, same PROPS sets'])

# ---------------------------------------------------------------- Hashin 3D
src = 'marioruiarruda__Hashin_3D_UMAT/umat_hashin3D_f90.f90'
names = ['E1', 'E2', 'E3', 'G12', 'G13', 'G23', 'v12', 'v13', 'v23', 'Xt', 'Xc', 'Yt', 'Yc', 'Zt', 'Zc', 'Sl', 'St', 'Si', 'Gft', 'Gfc', 'Gmt', 'Gmc', 'Git', 'Gic', 'etaft', 'dmax', 'alpha_f', 'alpha_i', 'presft', 'presfc', 'presmt', 'presmc', 'presit', 'presic']
pm = pmap(src, [(i + 1, n) for i, n in enumerate(names)]) + [dict(index=35, name='unused', code="2-Inputs_Outputs.txt: 'props(35) ! NOT USED' ... 'must be specified equal to ZERO'")]
hA = {k['index']: k for k in HARVEST[src]['constants']}
unit_of = lambda i: '-' if i in (7, 8, 9) else ('MPa' if i <= 18 else ('N/mm' if i <= 24 else ('s' if i == 25 else '-')))
csA = []
for i in range(1, 36):
    if i in hA:
        csA.append(c(i, hA[i]['name'], hA[i]['value'], unit_of(i) if i != 35 else '-', f"author-published (Arruda et al. 2023, Tables 1-2 / instructions), harvest confidence {hA[i]['confidence']}", 'author-kept'))
csA_extra = {18: c(18, 'Si', 67.0, 'MPa', "paper: interlaminar properties 'the same as the matrix'; matrix transverse shear St=67 chosen (Sl=64 is the alternative)", 'chosen')}
for i in range(29, 35):
    csA_extra[i] = c(i, names[i - 1], 0.05, '-', "fraction of strength; paper recommends 1%-10% residual stress, midpoint 5% chosen", 'chosen')
csA = sorted(csA + list(csA_extra.values()), key=lambda k: k['index'])
SA = ortho_S(29600, 11900, 11900, 0.27, 0.27, 0.30, 2900, 3000, 3000)
cfrp = dict(E1=171420.0, E2=9080.0, E3=9080.0, G12=5290.0, G13=5290.0, G23=3131.0, v12=0.32, v13=0.32, v23=0.45,
            Xt=2326.2, Xc=1200.1, Yt=62.3, Yc=199.8, Zt=62.3, Zc=199.8, Sl=92.3, St=75.3, Si=92.3,
            Gft=81.5, Gfc=106.3, Gmt=0.2774, Gmc=0.7879, Git=0.2774, Gic=0.7879, etaft=2e-5, dmax=1.0, alpha_f=1.0, alpha_i=1.0,
            presft=0.01, presfc=0.01, presmt=0.01, presmc=0.01, presit=0.01, presic=0.01)
CAM = 'Camanho, Maimi, Davila 2007 Compos Sci Technol 67:2715 (NASA NTRS 20070035071), verified by Scout d21_lookups.json L-HASHIN-1: '
LKUP = {'E1': CAM + 'Table 1 E1 171.42 GPa', 'E2': CAM + 'Table 1 E2 9.08 GPa', 'G12': CAM + 'Table 1 G12 5.29 GPa', 'v12': CAM + 'Table 1 nu12 0.32',
        'Xt': CAM + 'Table 2 XT 2326.2 MPa', 'Xc': CAM + 'Table 2 XC 1200.1 MPa', 'Yt': CAM + 'Table 2 YTud 62.3 MPa', 'Yc': CAM + 'Table 2 YC 199.8 MPa',
        'Sl': CAM + 'Table 2 SLud 92.3 MPa', 'Gft': CAM + 'Table 5 G1+ 81.5 kJ/m2', 'Gfc': CAM + 'Table 5 G1- 106.3 kJ/m2'}
basisB = {**LKUP, 'E3': 'chosen = E2 (transverse isotropy assumption; not in Camanho)', 'G13': 'chosen = G12 (transverse isotropy)', 'v13': 'chosen = v12 (transverse isotropy)',
          'G23': 'chosen = E2/(2(1+v23)) (transverse isotropy)', 'v23': 'chosen: transverse nu inside the uncited handbook range 0.4-0.5', 'Zt': 'chosen = Yt (transverse isotropy)', 'Zc': 'chosen = Yc', 'St': 'chosen: transverse shear strength between Yt and Sl (not in Camanho)',
          'Si': 'chosen = Sl (interlaminar ~ in-plane shear)', 'Gmt': CAM + 'Table 3 p.40 G2+ 0.2774 kJ/m2 (measured; kept under R-7 with council CELENT 0.15 mm: snap-back limit 2*Yt^2*Lc/(2*E2)=0.064 N/mm)',
          'Gmc': CAM + 'Table 3 p.40 G6 0.7879 kJ/m2; mapping the code matrix-compression energy to the measured shear energy G6 is an INTERPRETATION (R-7: kept with CELENT 0.15 mm, limit 0.66 N/mm)', 'Git': 'chosen = Gmt (interlaminar = matrix, as the author\'s paper does for GFRP)', 'Gic': 'chosen = Gmc (interlaminar = matrix)', 'etaft': 'viscous regularisation x2 of set A, still << increment time',
          'dmax': "author instruction '(insert 1.0)'", 'alpha_f': "author instruction '(insert 1.0)'", 'alpha_i': "author instruction '(insert 1.0)'"}
csB = []
for i, n in enumerate(names, 1):
    b = basisB.get(n, 'author lower bound of the 1%-10% residual-stress range')
    conf = 'author-kept' if n in ('dmax', 'alpha_f', 'alpha_i') else ('interpreted' if n == 'Gmc' else ('looked-up' if n in LKUP or n == 'Gmt' else 'chosen'))
    csB.append(c(i, n, cfrp[n], unit_of(i), b, conf))
csB.append(c(35, 'unused', 0.0, '-', "author: 'must be specified equal to ZERO'", 'author-kept'))
SB = ortho_S(171420, 9080, 9080, 0.32, 0.32, 0.45, 5290, 5290, 3131)
LC_HASHIN = 0.15  # mm, council CELENT (R-7)
def snap(sig, E, G, Lc=LC_HASHIN): return G > 2 * sig * sig * Lc / (2 * E)
sets = [dict(set_id='A', label='author GFRP + council Si/residuals', material='GFRP of Arruda et al. 2023 (CT test)', independence='base set',
             constants=csA, validity=dict(positive_definite_S=pd(SA)[0], min_eig_S=pd(SA)[1],
                                          no_snapback_at_council_celent=all([snap(323, 29600, 100), snap(426, 29600, 100), snap(71, 11900, 20), snap(121, 11900, 20)])),
             activation='fibre tension onset Xt/E1 = 1.09% (0.55 x small-strain ceiling); simple shear Sl/G12 = 2.2% (engineering)'),
        dict(set_id='B', label='CFRP class', material='IM7/8552-class carbon/epoxy UD', independence='different material of the same class (E1 x5.8, Xt x7.2, G_m x0.025-0.25)',
             constants=csB, validity=dict(positive_definite_S=pd(SB)[0], min_eig_S=pd(SB)[1],
                                          no_snapback_at_council_celent=all([snap(2326.2, 171420, 81.5), snap(1200.1, 171420, 106.3), snap(62.3, 9080, 0.2774), snap(199.8, 9080, 0.7879)])),
             activation='fibre tension onset Xt/E1 = 1.36% (0.68 x ceiling); reverse segment reaches -0.68% (Xc/E1 = 0.70%: compression onset marginal)')]
row(src, material_class='UD fibre-reinforced polymer laminate (3D Hashin damage)', class_basis="paper names GFRP (Arruda et al., Appl. Sci. 2023); class = UD FRP",
    unit_system='MPa, mm, s (author tables: MPa and MPa.mm)', props_map=pm, sets=sets, nstatv=51,
    nstatv_basis="2-Inputs_Outputs.txt: 'It contains 51 output state variables (nstatv=51)'; code zeroes 1..nstatv at kinc==1",
    initial_statev='0 (code zeroes at kinc==1)',
    status='licence_hold', licence_hold="D-21a Licence: 'all rights reserved ... no part may be reproduced or used in any manner without written permission' -> excluded from verification and counting until Santiago decides (default excluded)",
    celent="CELENT enters damage evolution: 'catLc=celent' (:260) -> calc_*_damage; council CHOICE (non-PROPS, R-5/R-7): element size 0.15 mm so CELENT ~ 0.15 mm for both sets (Lc <= 0.18 mm needed for measured Gmc, <= 0.65 mm for Gmt); record the value Abaqus passes",
    kinc1_statev_reset="'if (kinc == 1) then; do i=1,nstatv; statev(i)=ZERO' (:143-146): every STATEV reset at the first increment of EVERY step",
    flags=['element characteristic length CELENT enters damage evolution; snap-back checks use the council CELENT 0.15 mm'],
    lookups=[dict(id='L-HASHIN-1', status='answered by Scout (d21_lookups.json): confirmed, Xt->2326.2, Xc->1200.1 applied', source=src, constants='set B: E1,E2,G12,v12,Xt,Xc,Yt,Yc,Sl,Gft,Gfc (and GIc/GIIc for comparison)', material_class='IM7/8552 carbon/epoxy UD',
                  what='a published table (e.g. Camanho et al. 2007 Compos. Part A 38:2050, or the NASA/NCAMP IM7/8552 data) with page/table numbers; confirm or correct the recalled values. Gmt/Gmc stay council-chosen (snap-back margin).', priority='medium')])

# ---------------------------------------------------------------- Mazars concrete
src = 'marioruiarruda__Mazars_UMAT/umat_mazars_f90.f90'
mz = [(1, 'E'), (2, 'nu'), (3, 'fctm'), (5, 'GfIt'), (6, 'GfIc'), (8, 'eta'), (9, 'dmaxt'), (10, 'dmaxc'), (12, 'pt'), (13, 'pc'),
      (15, 'At'), (16, 'Ac'), (17, 'Bt'), (18, 'Bc'), (19, 'ec1'), (20, 'ec2'), (21, 'fcm')]
pm = pmap(src, mz) + [dict(index=i, name='not used', code=f"2-Inputs_Outputs.txt: 'props({i})   ! NOT USED' (code never reads it; must be 0.0)") for i in (4, 7, 11, 14)]
def mazars(set_id, label, mat, E, fctm, fcm, ec1, ec2, eta, pt, pc, GfIc, indep):
    Gf = 73.0 * fcm ** 0.18 / 1000.0
    vals = {1: (E, 'MPa', f'EC2 Table 3.1 Ecm for {mat}', 'class-typical'), 2: (0.2, '-', 'EC2 3.1.3(4)', 'class-typical'),
            3: (fctm, 'MPa', f'EC2 Table 3.1 fctm for {mat}', 'class-typical'), 4: (0.0, '-', "author: 'NOT USED ... defined as 0.0'", 'author-kept'),
            5: (round(Gf, 4), 'N/mm', f'MC2010 eq. 5.1-9 Gf = 73*fcm^0.18 N/m, fcm={fcm}', 'class-typical'), 6: (GfIc, 'N/mm', 'typical compressive fracture energy of normal concrete (10-30 N/mm)', 'chosen'),
            7: (0.0, '-', 'not used', 'author-kept'), 8: (eta, 's', 'viscous regularisation << increment time (near rate independent)', 'chosen'),
            9: (1.0, '-', "author instruction '(Insert 1.0)'", 'author-kept'), 10: (1.0, '-', "author instruction '(Insert 1.0)'", 'author-kept'),
            11: (0.0, '-', 'not used', 'author-kept'), 12: (pt, '-', "fraction; author example '(10% then insert 0.1)'", 'chosen'), 13: (pc, '-', 'residual compressive fraction', 'chosen'),
            14: (0.0, '-', 'not used', 'author-kept'), 15: (0.0, '-', 'At: only used when GfIt<=0 (classical Mazars branch); author doc says define 0.0', 'author-kept'),
            16: (0.0, '-', 'Ac: as At', 'author-kept'), 17: (0.0, '-', 'Bt: as At', 'author-kept'), 18: (0.0, '-', 'Bc: as At', 'author-kept'),
            19: (ec1, '-', f'EC2 Table 3.1 eps_c1 for {mat}', 'class-typical'), 20: (ec2, '-', f'EC2 Table 3.1 eps_cu1 for {mat}', 'class-typical'),
            21: (fcm, 'MPa', f'EC2 Table 3.1 fcm for {mat}', 'class-typical')}
    names = {1: 'E', 2: 'nu', 3: 'fctm', 4: 'unused', 5: 'GfIt', 6: 'GfIc', 7: 'unused', 8: 'eta', 9: 'dmaxt', 10: 'dmaxc', 11: 'unused', 12: 'pt', 13: 'pc', 14: 'unused', 15: 'At', 16: 'Ac', 17: 'Bt', 18: 'Bc', 19: 'ec1', 20: 'ec2', 21: 'fcm'}
    cs = [c(i, names[i], v[0], v[1], v[2], v[3]) for i, v in sorted(vals.items())]
    ed0 = fctm / E; eu = Gf / (1.0 * E * ed0) + ed0
    return dict(set_id=set_id, label=label, material=mat, independence=indep, constants=cs,
                validity=dict(positive_definite=pd(iso_C(E, 0.2))[0], nu_lt_half=True, tension_softening_eu_gt_ed0=eu > 2 * ed0, ec1_lt_ec2=ec1 < ec2),
                activation=f'tension damage onset eps = fctm/E = {ed0:.2e} (far below ceiling); compression branch from eps_c1 = {ec1}')
sets = [mazars('A', 'C30/37', 'concrete C30/37', 33000.0, 2.9, 38.0, 0.0022, 0.0035, 1e-4, 0.10, 0.10, 20.0, 'base set'),
        mazars('B', 'C50/60', 'concrete C50/60', 37000.0, 4.1, 58.0, 0.00245, 0.0035, 1.3e-4, 0.07, 0.13, 26.0, 'different strength class (fctm +41%, fcm +53%); eta, pt, pc, GfIc changed by 30%')]
row(src, material_class='normal-weight concrete (Mazars-type damage)', class_basis="2-Inputs_Outputs.txt:2 'The values of concrete properties are described in EC2 and MC2010'",
    unit_system='MPa, mm, s', props_map=pm, sets=sets, nstatv=10,
    nstatv_basis="2-Inputs_Outputs.txt: 'It contains 10 output state variables (nstatv=10)'", initial_statev="code zeroes STATEV at kinc==1 and sets STATEV(7)=fctm/E",
    status='licence_hold', licence_hold="D-21a Licence: 'all rights reserved' -> excluded until Santiago decides (default excluded)",
    celent="CELENT passed to calc_damage_t/calc_damage_c (fracture-energy regularisation eu = Gf/(CELENT*E*ed0)+ed0); council element size 1 mm",
    kinc1_statev_reset="'if (kinc == 1) then; do i=1,nstatv; statev(i)=ZERO' and 'if (kinc==1) statev(7)=ed0' ('PROBLEMATIC FOR MORE THAN ONE LOAD STEP'): reset at the first increment of every step",
    lookups=[dict(id='L-EC2-1', source=src, constants='set A/B: Ecm, fctm, fcm, eps_c1, eps_cu1 (C30/37, C50/60); Gf formula', material_class='normal-weight concrete',
                  what='R-4: verify EN 1992-1-1 Table 3.1 rows C30/37 and C50/60 and fib MC2010 eq. 5.1-9 (Gf = 73 fcm^0.18) with page/table; values stand only once verified', priority='medium')],
    flags=['code/doc conflict: code reads props(15..18) as At,Ac,Bt,Bc; with GfIt,GfIc>0 they are unused, set to 0.0 per doc',
           'optional extra branch coverage (NOT part of the counted sets): GfIt=GfIc=0 with At=1.0, Bt=1e4, Ac=1.2, Bc=1500 exercises the classical Mazars branch'])

# ---------------------------------------------------------------- abuganza growth (author deck + designated LHS points)
for src, dup in [('abuganza__BayesianCalibrationSkinGrowth/Revision/Abaqus SImulation/Isotropic/BC1_50cc/Iso_50cc.f', None),
                 ('abuganza__BayesianCalibrationSkinGrowth/Revision/Abaqus SImulation/Isotropic/BC1_60cc/Iso_60cc.f', None),
                 ('abuganza__BayesianCalibrationSkinGrowth/Revision/Abaqus SImulation/Isotropic/BC2_60cc/Iso_60cc.f', 'abuganza__BayesianCalibrationSkinGrowth/Revision/Abaqus SImulation/Isotropic/BC1_60cc/Iso_60cc.f')]:
    pm = pmap(src, [(1, 'lam'), (2, 'mu'), (3, 'xn0_1'), (4, 'xn0_2'), (5, 'xn0_3'), (6, 'kk'), (7, 'tcr'), (8, 'm'), (9, 'n')])
    d = str(Path(src).parent)
    def isoset(set_id, rown, lam, mu, kk, indep):
        lhs = f"{d}/Iso_lam_mu_k.txt row {rown}"
        return dict(set_id=set_id, label=f'LHS row {rown}', material='porcine skin (author design point)', independence=indep,
                    constants=[c(1, 'lam', lam, 'unstated (author)', f"{lhs}, formatted '%.3f' as parastudy_growth.py writes it; designated by the council corner rule (D-21a b)", 'author-other-context'),
                               c(2, 'mu', mu, 'unstated (author)', f"{lhs}, '%.3f'; council corner rule", 'author-other-context'),
                               c(3, 'xn0_1', 0.0, '-', "author script 'xn0_1=0.'", 'author-kept'), c(4, 'xn0_2', 0.0, '-', "author script 'xn0_2=0.'", 'author-kept'),
                               c(5, 'xn0_3', 1.0, '-', "author script 'xn0_3=1.'", 'author-kept'),
                               c(6, 'kk', kk, 'rate (author time unit)', f"{lhs}, '%.3f'; council corner rule", 'author-other-context'),
                               c(7, 'tcr', 1.1982, 'stretch', "author script 'tcrt=1.1982'", 'author-kept'),
                               c(8, 'm', 0.0, '-', "author script 'mm=0.'", 'author-kept'), c(9, 'n', 0.0, '-', "author script 'nn=0.'", 'author-kept')],
                    validity=dict(mu_gt_0=mu > 0, lam_gt_0=lam > 0, nu=round(lam / (2 * (lam + mu)), 4)),
                    activation="growth needs stretch above tcr=1.1982: driven by the author's own expander deck (PID volume control), whose loading the author designed to exceed it")
    sets = [isoset('A', 1, 0.490, 0.666, 0.746, 'base set: low corner of the author LHS design (lowest lam/mu level, lowest kk)'),
            isoset('B', 30, 0.598, 0.814, 1.599, 'high corner of the author LHS design: lam,mu +22%, kk +114%')]
    row(src, material_class='skin (tissue expansion), neo-Hookean + area growth', class_basis='author Bayesian calibration study (porcine skin); LHS design file in the same directory',
        unit_system="author's (unstated; MPa and hours by the paper's 'k in [0.02,0.08] 1/h' convention) — values taken verbatim from the author's design file",
        props_map=pm, sets=sets, nstatv=6, nstatv_basis="author deck Iso_BC*.inp '*Depvar 6'", initial_statev="author deck '*INITIAL CONDITIONS, TYPE=SOLUTION, USER' (SDVINI in source)",
        experiment_origin='author_deck_with_council_parameters', status='covered', duplicate_of=dup, counts_in_tier=dup is None,
        flags=['experiment is the AUTHOR deck (Iso_BC*.inp) plus a generated param.param; D-21 designates which LHS design points are used (the paper designates none)',
               'the UMAT file also holds the author PID/fluid-cavity controller; run only with the author deck', 'D-1/D-2 status of the repository to be checked by Vera before any push'] + ([f'duplicate_of {dup} (different deck: BC2)'] if dup else []))
for src in ['abuganza__BayesianCalibrationSkinGrowth/Revision/Abaqus SImulation/GOH/BC1_50cc/GOH_50cc.f',
            'abuganza__BayesianCalibrationSkinGrowth/Revision/Abaqus SImulation/GOH/BC1_55cc/GOH_55cc.f']:
    nm = ['k(bulk)', 'mu', 'kappa', 'k1', 'k2', 'f0_1', 'f0_2', 'f0_3', 'xn0_1', 'xn0_2', 'xn0_3', 'kkg1', 'kkg2', 'mg1', 'mg2', 'ng1', 'ng2', 'tcr1', 'tcr2']
    pm = pmap(src, [(i + 1, n) for i, n in enumerate(nm)])
    d = str(Path(src).parent)
    fixed = {3: (0.0498, "kappa=0.0498"), 4: (4.97, "k1= 4.97"), 5: (2.88, "k2=2.88"), 6: (1.0, "f0_1=1."), 7: (0.0, "f0_2=0."), 8: (0.0, "f0_3=0."),
             9: (0.0, "xn0_1=0."), 10: (0.0, "xn0_2=0."), 11: (1.0, "xn0_3=1."), 14: (0.0, "mg1=0."), 15: (0.0, "mg2=0."), 16: (0.0, "ng1=0."), 17: (0.0, "ng2=0."),
             18: (1.1254, "tcr1=1.1254"), 19: (1.1175, "tcr2=1.1175")}
    def gohset(set_id, rown, mu, k, g1, g2, indep):
        lhs = f"{d}/Anis_mu_k_G1_G2.txt row {rown}"
        cr = '; council corner rule (D-21a b)'
        cs = [c(1, 'k(bulk)', k, 'unstated (author)', f"{lhs} column 2, '%.3f'" + cr, 'author-other-context'), c(2, 'mu', mu, 'unstated (author)', f"{lhs} column 1, '%.3f'" + cr, 'author-other-context'),
              c(12, 'kkg1', g1, 'rate (author time unit)', f"{lhs} column 3, '%.3f'" + cr, 'author-other-context'), c(13, 'kkg2', g2, 'rate (author time unit)', f"{lhs} column 4, '%.3f'" + cr, 'author-other-context')]
        cs += [c(i, nm[i - 1], v, '-', f"author script parastudy_growth.py '{q}'", 'author-kept') for i, (v, q) in fixed.items()]
        return dict(set_id=set_id, label=f'LHS row {rown}', material='porcine skin, GOH (author design point)', independence=indep,
                    constants=sorted(cs, key=lambda x: x['index']), validity=dict(mu_gt_0=True, k_gt_0=True, kappa_in_0_third=0 <= 0.0498 <= 1 / 3),
                    activation='growth for fibre/normal stretch above tcr1/tcr2, driven by the author expander deck')
    sets = [gohset('A', 1, 0.045, 0.216, 1.070, 0.517, 'base set: low corner of the author LHS design'),
            gohset('B', 75, 0.055, 0.264, 2.171, 0.996, 'high corner of the author LHS design: mu,k +22%, kkg1 +103%, kkg2 +93%')]
    row(src, material_class='skin (tissue expansion), GOH anisotropic + 2-direction growth', class_basis='author study; LHS design file Anis_mu_k_G1_G2.txt',
        unit_system="author's (unstated) — values verbatim from the author's design file", props_map=pm, sets=sets, nstatv=21,
        nstatv_basis="author deck GOH_BC1.inp '*Depvar 21'", initial_statev="author deck '*INITIAL CONDITIONS, TYPE=SOLUTION, USER'",
        experiment_origin='author_deck_with_council_parameters',
        flags=['experiment is the AUTHOR deck (GOH_BC1.inp) plus a generated param.param (author also writes p=0.03, t_init=0.001, t_max=0.001)',
               'D-1/D-2 status of the repository to be checked by Vera before any push'])

# ---------------------------------------------------------------- mholla prescribed growth (_Abaqus variants)
def nh(lam, mu): return dict(nu=round(lam / (2 * (lam + mu)), 4), E=round(mu * (3 * lam + 2 * mu) / (lam + mu), 4))
for src, kind in [('mholla__growth/umats/umat_area_morph_Abaqus.f', 'area'), ('mholla__growth/umats/umat_fiber_morph_Abaqus.f', 'fiber'),
                  ('mholla__growth/umats/umat_iso_morph_Abaqus.f', 'iso')]:
    spec = [(1, 'lam'), (2, 'mu'), (3, 'tmax'), (4, 'tau')]
    if kind != 'iso':
        spec += [(5, 'dir_1'), (6, 'dir_2'), (7, 'dir_3')]
    pm = pmap(src, spec)
    def gset(set_id, lam, mu, tmax, tau, direction, indep, cls):
        cs = [c(1, 'lam', lam, 'normalised (E=1)', f'{cls}', 'chosen'), c(2, 'mu', mu, 'normalised (E=1)', f'{cls}', 'chosen'),
              c(3, 'tmax', tmax, '-', 'final growth multiplier; growth well above the 1% gate', 'chosen'),
              c(4, 'tau', tau, 'time unit of the step', 'growth time constant = tau; chosen <= 0.4 x council total time 1.0 so theta_g reaches > 90% of tmax-1', 'chosen')]
        if kind != 'iso':
            for j, v in enumerate(direction):
                cs.append(c(5 + j, f'dir_{j + 1}', v, '-', 'growth direction (D-21 cond. 5 orientation, council-chosen)', 'chosen'))
        thg = (tmax - 1) * (1 - math.exp(-1.0 / tau)) + 1
        return dict(set_id=set_id, label=cls.split(';')[0], material=cls, independence=indep, constants=cs,
                    non_props_choices=[dict(input='total time of the growth step', value=1.0, T_over_tau=round(1.0 / tau, 4), loading_origin='council_choice',
                                            basis="D-21a (a): theta_g = (tmax-1)(1-exp(-time(2)/tau))+1 depends on time only through time/tau (tau = PROPS(4)) and is defined and bounded for all t >= 0 (tau > 0)", confidence='chosen')],
                    validity=dict(**nh(lam, mu), mu_gt_0=mu > 0, theta_g_at_T=round(thg, 4)),
                    activation=f'theta_g(t=1) = {thg:.3f} (growth {100 * (thg - 1):.1f}% >= 1% gate)')
    sets = [gset('A', 0.577, 0.385, 1.5, 0.25, (0.0, 0.0, 1.0), 'base set', 'compressible neo-Hookean, E=1, nu=0.3 (the values every sibling deck in mholla/growth input_files uses)'),
            gset('B', 3.105, 0.345, 1.2, 0.4, (0.7071067812, 0.7071067812, 0.0), 'near-incompressible soft tissue nu=0.45 (lam x5.4); tmax-1 -60%, tau +60%; direction rotated', 'nearly incompressible soft tissue, E=1, nu=0.45')]
    row(src, material_class='soft biological tissue, neo-Hookean with prescribed morphogenetic growth', class_basis='repository (Holland lab growth UMATs); the README pairs sibling decks with lam=0.577, mu=0.385',
        unit_system='normalised (stiffness relative to E=1; time in step units)', props_map=pm, sets=sets, nstatv=3,
        nstatv_basis='SDVINI sets statev(1..3)=1 and the UMAT writes statev(1..3)', initial_statev='1,1,1 from the SDVINI in the same file',
        reads_coords_or_noel=False, coords_note='COORDS/NOEL passed to the inner routine but not used', status='covered',
        flags=['growth total time council-chosen under D-21a (a), recorded with T/tau', 'needs SDVINI support in the council deck (*INITIAL CONDITIONS, TYPE=SOLUTION, USER)'])

for src in ['mholla__growth/umats/umat_neohooke.f', 'mholla__growth/umats/umat_neohooke_abaqus.f']:
    pm = pmap(src, [(1, 'lam'), (2, 'mu')])
    sets = [dict(set_id='A', label='nu=0.3', material='compressible neo-Hookean, E=1, nu=0.3', independence='base set',
                 constants=[c(1, 'lam', 0.577, 'normalised', 'sibling-deck value (E=1, nu=0.3)', 'chosen'), c(2, 'mu', 0.385, 'normalised', 'sibling-deck value', 'chosen')],
                 validity=nh(0.577, 0.385), activation='hyperelastic: finite-strain response at the 0.2 stretch default'),
            dict(set_id='B', label='nu=0.45', material='nearly incompressible soft tissue, E=1, nu=0.45', independence='lam x5.4, mu -10%',
                 constants=[c(1, 'lam', 3.105, 'normalised', 'E=1, nu=0.45', 'chosen'), c(2, 'mu', 0.345, 'normalised', 'E=1, nu=0.45', 'chosen')],
                 validity=nh(3.105, 0.345), activation='hyperelastic')]
    row(src, material_class='compressible neo-Hookean (soft tissue, normalised)', class_basis='repository; sibling decks lam=0.577, mu=0.385', unit_system='normalised',
        props_map=pm, sets=sets, nstatv=1 if src.endswith('umat_neohooke.f') else 0, nstatv_basis='SDVINI statev(1)=1' if src.endswith('umat_neohooke.f') else 'no STATEV use',
        initial_statev='1 (SDVINI)' if src.endswith('umat_neohooke.f') else None, status='covered_blocked_non_data',
        flags=['registry compiled=False: source defect (umat_neohooke.f: stray ")" in the inner-routine header; umat_neohooke_abaqus.f: calls umat_neohooke but defines umat_neohooke_Abaqus) — not data'])

# ---------------------------------------------------------------- shayansss hml NONLIPLS (cartilage)
src = 'shayansss__hml/NONLIPLS.for'
pm = pmap(src, [(1, 'E1MP'), (2, 'E2MP'), (3, 'ALPHA1')])
sets = [dict(set_id='A', label='healthy cartilage fibrils', material='healthy articular cartilage (author pair E0 4.63 / Eepsilon 3670)', independence='base set',
             constants=[c(1, 'E1MP', 4.63, 'MPa', "L-CART-1 (Scout, verified): the author's own paper Sajjadinia et al. 2019 Proc IMechE H 233:871, Table 1 'E0 (MPa) 4.63', and sibling code bioumat SUBROUTINES.FOR:270 'E1MP=4.63D0'", 'author-other-context'),
                        c(2, 'E2MP', 3670.0, 'MPa', "L-CART-1: author's paper Table 1 'Eepsilon (MPa) 3670', sibling code SUBROUTINES.FOR:271 'E2MP=3670D0'; this code ':329 E2MP=3670/FOUR ! FOR OA'", 'author-other-context'),
                        c(3, 'ALPHA1', 0.0075, '-', "midpoint of the author's sampling range 'np.random.uniform(0.005,0.010)' (2d.py:295)", 'chosen')],
             validity=dict(E1_gt_0=True, E2_ge_0=True), activation='fibrils carry tension only (strain > 0): uniaxial tension activates the nonlinear term E2*eps; finite strain'),
        dict(set_id='B', label='OA cartilage', material="osteoarthritic (degenerated) cartilage per the author's Table 1", independence='different material of the same class: Eepsilon -75% (author OA value), ALPHA1 +33%; E0 kept (author lists one E0)',
             constants=[c(1, 'E1MP', 4.63, 'MPa', "Sajjadinia 2019 Table 1 'E0 (MPa) 4.63' (single value) / bioumat SUBROUTINES.FOR:270", 'author-other-context'),
                        c(2, 'E2MP', 917.5, 'MPa', "Sajjadinia 2019 Table 1 'Eepsilon (MPa) 3670 917.5' (degenerated) = this code's ':328-329 IF (STATEV(1).NE.1) E2MP=3670/FOUR ! FOR OA'; passed via PROPS(2) because SDVINI sets STATEV(1)=1 (:160), so the code's own OA branch is not reached", 'author-other-context'),
                        c(3, 'ALPHA1', 0.0100, '-', "upper end of the author's range 0.005-0.010 (+33% vs set A)", 'chosen')],
             validity=dict(E1_gt_0=True, E2_ge_0=True), activation='as set A')]
row(src, material_class='articular cartilage (fibril-reinforced poro-hyperelastic, NONLIPLS)', class_basis="code comments (fibrillar constants, GAG, 'FOR OA'); README (cartilage ML study)",
    unit_system='MPa, mm', props_map=pm, sets=sets, nstatv=90, nstatv_basis='SDVINI comment block: STATEV 82-90 = initial DFGRD1 (highest index 90)',
    initial_statev="SDVINI: opens FILE='C:\\temp\\HybridML\\DATA.txt'; council input file with first line '0' selects the author's hard-coded study branch (STATEV(5)=-1, (4)=0.01, (2)=0.39, (3)=0.15)",
    reads_coords_or_noel=True, coords_note="COORDS/NOEL are read only in the SDVINI file branch (first line /= 0); with the council '0' file they are not read; UMAT body does not read them",
    status='covered_blocked_non_data',
    flags=["needs the harness to place an auxiliary input file literally named 'C:\\temp\\HybridML\\DATA.txt' (content '0') in the run directory — helper support, not data; recorded as non-PROPS initial-state choice",
           "author's other materials of the .cae model are not needed for a single-material probe", 'JSTEP(1)=1 sets ALPHA2=0 (GAG pressure off in step 1): single-step probe exercises the fibril + solid matrix only'],
    lookups=[dict(id='L-CART-1', status='answered by Scout: 4.316 belonged to another fibril law; 4.63 applied', source=src, constants='E1MP, E2MP', material_class='articular cartilage collagen fibrils (fibril-reinforced poroviscoelastic model)',
                  what='Wilson et al. 2004 J Biomech 37:357 (or 2005) table of fibril constants E1 (linear) and E2 (nonlinear) with page/table; confirm 4.316 MPa and 3670 MPa', priority='low')])

# ---------------------------------------------------------------- PavementDesign ms_plast (viscoplastic)
src = 'RafalMichalczyk__PavementDesign/Subroutines/umat_ms_plast.for'
pm = pmap(src, [(1, 'K (xvol)'), (2, 'G (xg)'), (3, 'yield'), (4, 'alpha'), (5, 'n'), (6, 'mu (viscosity)')])
def msp(set_id, label, mat, K, G, y, a, n, mu, indep, conf):
    E = 9 * K * G / (3 * K + G); nu = (3 * K - 2 * G) / (2 * (3 * K + G))
    svm = math.sqrt(3) * y  # ||dev s|| > sqrt(2)*y  <=> sigma_vm > sqrt(3)*y
    cs = [c(1, 'K', K, 'MPa', f'{mat}: bulk modulus from E={E:.0f} MPa, nu={nu:.2f}', conf), c(2, 'G', G, 'MPa', f'{mat}: shear modulus', conf),
          c(3, 'yield', y, 'MPa', f'{mat}: viscoplastic threshold', 'chosen'), c(4, 'alpha', a, '-', 'pressure sensitivity of the threshold', 'chosen'),
          c(5, 'n', n, '-', 'integer exponent keeps x1**(n-2) real in the Newton loop', 'chosen'),
          c(6, 'mu', mu, 's', 'viscosity time scale near the 1 s probe period (rate effect visible between base and 100x fast run)', 'chosen')]
    return dict(set_id=set_id, label=label, material=mat, independence=indep, constants=cs,
                validity=dict(positive_definite=pd(iso_C(E, nu))[0], nu=round(nu, 3), nu_lt_half=nu < 0.5),
                activation=f'threshold sigma_vm > sqrt(3)*yield = {svm:.3f} MPa -> strain ~ {svm / E:.1e}; flow lags one increment (uses STATEV of the previous increment)')
sets = [msp('A', 'asphalt concrete', 'asphalt concrete at ~20 C', 4444.0, 1481.0, 0.5, 0.2, 2.0, 1.0, 'base set', 'class-typical'),
        msp('B', 'unbound granular base', 'unbound granular base course', 200.0, 120.0, 0.05, 0.3, 3.0, 0.3, 'different pavement material (K -95%, yield -90%, n +50%, mu -70%)', 'class-typical')]
row(src, material_class='pavement material (viscoplastic)', class_basis='repository PavementDesign', unit_system='MPa, s', props_map=pm, sets=sets, nstatv=2,
    nstatv_basis='STATEV(1)=||dev s||, STATEV(2)=tr(s) (umat_ms_plast.for, last lines)', initial_statev='0 (zero stress)',
    flags=['the stress update multiplies engineering shear strain by 2G (devstraininc(i+3)=dstran(i+3)); original behaviour, compared as is', 'family reviewed as rate dependent: rate probe needed'])

# ---------------------------------------------------------------- Leonov (bessagroup): author names the materials 'pe' and 'pp'
def eyring(sigma_y, tau_star, dH, rate=0.35):
    """A* so that tau = sigma_y/sqrt(3) at equivalent shear rate `rate` (1/s): sinh(tau/tau*)/(A* e^{dH/RT}) = rate."""
    T = 296.0
    tau = sigma_y / math.sqrt(3)
    C1 = math.sinh(tau / tau_star) / rate
    return C1 * math.exp(-dH / (R_GAS * T)), R_GAS * T / tau_star
PP = dict(name='isotactic polypropylene (author material "pp")', E=1500.0, nu=0.40, sy=30.0, ts=1.0, dH=1.58e8, mu=0.10, h=20.0, D=2.0, H=5.0, gt=1.0, lam=0.10, G1=300.0)
PE = dict(name='high-density polyethylene (author material "pe")', E=1000.0, nu=0.42, sy=22.0, ts=0.8, dH=1.41e8, mu=0.415, h=15.0, D=1.5, H=3.0, gt=0.5, lam=0.15, G1=200.0)
PP.update(dH_basis="Ree-Eyring process II dU = 158.0 kJ/mol (van Erp 2012 PhD TU/e, p.42 Table 2.2, verified by Scout L-LEONOV-1) x 1e6 -> mJ/mol (unit conversion = interpreted; choosing process II = chosen)",
          mu_basis='pressure coefficient, chosen 0.10 (not tabulated for iPP by van Erp)', mu_conf='chosen')
PE.update(dH_basis="Ree-Eyring process II dU = 141 kJ/mol (Kanters 2015 PhD TU/e, p.21-22 Table 2.3, verified by Scout L-LEONOV-1) x 1e6 -> mJ/mol (unit conversion = interpreted; choosing process II = chosen)",
          mu_basis="Kanters 2015 Table 2.3 'mu 0.415' for PE100 HDPE (verified by Scout L-LEONOV-1)", mu_conf='looked-up')
for m in (PP, PE):
    m['A'], m['vs'] = eyring(m['sy'], m['ts'], m['dH'])
def leo_consts(m, layout):
    b = {'E': (m['E'], 'MPa', f"{m['name']}: typical room-temperature modulus", 'class-typical'),
         'nu': (m['nu'], '-', 'typical semicrystalline polyolefin nu', 'class-typical'),
         'T': (296.0, 'K', 'room temperature', 'chosen'), 'p_atm': (0.1013, 'MPa', 'atmospheric pressure', 'class-typical'),
         'dH': (m['dH'], 'mJ/mol', m['dH_basis'], 'interpreted'),
         'A*': (float('%.4g' % m['A']), 's', f"chosen so the Eyring flow gives uniaxial yield ~{m['sy']} MPa (class-typical) at equivalent shear rate 0.35/s, T=296 K, without softening", 'chosen'),
         'v*': (float('%.4g' % m['vs']), 'mm3/mol', f"= R*T/tau*, tau*={m['ts']} MPa, chosen. v* in this code is the SHEAR-form activation volume (vp_leonov_model.f:94 tau_star=(R_gas*T)/v_star with C2=sqrt(1/2)*||s||). The thesis V (iPP 4.44, HDPE 3.17 nm3; shear form iPP 2.674e6, HDPE 1.909e6 mm3/mol) is NOT adopted because the thesis defining equation (shear vs tensile form) has not been quoted", 'chosen'),
         'mu': (m['mu'], '-', m['mu_basis'], m['mu_conf']),
         'hsoft': (m['h'], '-', 'softening rate (semicrystallines soften little)', 'chosen'),
         'Dinf': (m['D'], '-', 'saturated softening (small for semicrystallines)', 'chosen'),
         'H': (m['H'], 'MPa', 'strain-hardening modulus, class-typical few MPa', 'class-typical'),
         'gt': (m['gt'], 's', 'viscoelastic relaxation time at unit rate: near the 1 s probe period', 'chosen'),
         'lamda': (m['lam'], '-', 'rate exponent of the relaxation time', 'chosen'),
         'G1': (m['G1'], 'MPa', 'viscoelastic mode modulus ~ 0.2 x elastic shear modulus', 'chosen')}
    return [c(i + 1, k, b[k][0], b[k][1], b[k][2], b[k][3]) for i, k in enumerate(layout)]
VP = ['E', 'nu', 'dH', 'A*', 'v*', 'mu', 'hsoft', 'Dinf', 'H', 'T', 'p_atm']
VEVP = ['E', 'nu', 'T', 'p_atm', 'gt', 'lamda', 'G1', 'dH', 'A*', 'v*', 'mu', 'hsoft', 'Dinf', 'H']
base = 'bessagroup__f3dasm_simulate/src/f3dasm_simulate/abaqus/scriptbase/benchmark_abaqus_scripts/'
for fname, layout, nst, nstb in [('vp_leonov_model.f', VP, 15, "author CAE script veni_rve.py:200 'num_stv=15' (code writes up to STATEV(2*NTENS+2)=14)"),
                                  ('vevp_leonov_model.f', VEVP, 44, "author CAE script veni_rve.py:451 'num_stv=44' (code writes up to STATEV(7*NTENS+2)=44)")]:
    src = base + fname
    pm = pmap(src, [(i + 1, k) for i, k in enumerate(layout)])
    sets = []
    for sid, m, indep in (('A', PP, 'base set'), ('B', PE, 'different material of the same class (the author names both: "pe" and "pp"); E -33%, yield -27%, dH -20%, H -40%')):
        sets.append(dict(set_id=sid, label=m['name'].split(' (')[0], material=m['name'], independence=indep, constants=leo_consts(m, layout),
                         validity=dict(positive_definite=pd(iso_C(m['E'], m['nu']))[0], nu_lt_half=m['nu'] < 0.5, exp_argument_dH_over_RT=round(m['dH'] / (R_GAS * 296), 2)),
                         activation=f"yield strain ~ {m['sy'] / m['E']:.3f} (finite-strain ceiling 0.2); Eyring rate sensitivity: 100x faster run raises the flow stress by ~tau*ln(100)*sqrt(3) = {m['ts'] * math.log(100) * math.sqrt(3):.1f} MPa"))
    row(src, material_class='glassy/semicrystalline thermoplastic (Eyring-Leonov elasto-viscoplastic)', class_basis="author CAE scripts name the two materials paras_pe / paras_pp (veni_rve.py:118-119, 197-206)",
        unit_system="MPa, mJ/mol, mm3/mol, s, K (source comments in vp_leonov_model.f:79-89; R_gas=8314.46 mJ/(mol K) hard-coded)", props_map=pm, sets=sets, nstatv=nst, nstatv_basis=nstb,
        initial_statev='0 (STATEV read at increment start; zero = virgin)', reads_temp=False, reads_temp_note='temperature is PROPS (T), not the TEMP argument',
        flags=['finite strain (registry kinematics finite)'],
        lookups=[dict(id='L-LEONOV-1', source=src, constants='dH, v* (or tau*), A0, mu, H for iPP and HDPE', material_class='iPP and HDPE at room temperature (Eyring / EGP-type model)',
                      what='published Eyring/EGP parameter sets (e.g. van Erp et al., Senden et al., Klompen et al. 2005 for the PC template) with table refs; the chosen sets only need to be admissible and to place yield at class-typical stress, so this is a confirmation, not a blocker', priority='low')])

# ---------------------------------------------------------------- glu46 power-law creep (wood / shale)
def comp_ortho(E1, E2, E3, n12, n13, n23, G12, G13, G23):
    """Compliance in the code's PROPS order: 1:S11 2:S22 3:S33 4:S2323(->DDSDDE slot 6) 5:S1313 6:S1212 7:S12 8:S13 9:S23"""
    S = ortho_S(E1, E2, E3, n12, n13, n23, G12, G13, G23)
    return [S[0, 0], S[1, 1], S[2, 2], S[5, 5], S[4, 4], S[3, 3], S[0, 1], S[0, 2], S[1, 2]], S
PN = ['B11', 'B22', 'B33', 'B44(23 shear, Abaqus slot 6)', 'B55(13 shear)', 'B66(12 shear, Abaqus slot 4)', 'B12', 'B13', 'B23']
def creep_set(set_id, label, mat, eng, n, indep, conf, layers=1):
    B, S = comp_ortho(**eng)
    cs = []
    for L in range(layers):
        off = 18 * L
        for i in range(9):
            cs.append(c(off + i + 1, PN[i] + (f' layer{L + 1}' if layers > 1 else ''), float('%.6g' % B[i]), '1/MPa (at t = 1 s)', f'{mat}: compliance from engineering constants {eng}', conf))
        for i in range(9):
            cs.append(c(off + 10 + i, 'N' + PN[i][1:3] + (f' layer{L + 1}' if layers > 1 else ''), n, '-', 'power-law creep exponent J(t)=B t^n; same n for all components keeps J(t) positive definite for every t', 'chosen'))
    ok, emin = pd(S)
    return dict(set_id=set_id, label=label, material=mat, independence=indep, constants=cs,
                validity=dict(compliance_positive_definite=ok, min_eig_S=emin, uniform_exponent=True),
                activation=f'power-law creep: compliance grows as t^{n}; between the base run (period 1 s) and the 100x fast run the compliance differs by factor 100^{n} = {100 ** n:.2f}; hold of 10 periods shows creep/relaxation')
# axes: wood 1=R, 2=L, 3=T (Cube/Column rotate about y in the x-z (R-T) plane; y = L); shale 3 = normal to bedding (code comment)
SPRUCE = dict(E1=800.0, E2=12000.0, E3=450.0, n12=0.37 * 800 / 12000, n13=0.47, n23=0.42, G12=650.0, G13=40.0, G23=600.0)
BEECH = dict(E1=2280.0, E2=14000.0, E3=1160.0, n12=0.45 * 2280 / 14000, n13=0.60, n23=0.51, G12=1610.0, G13=460.0, G23=1060.0)
SHALE_A = dict(E1=25000.0, E2=25000.0, E3=15000.0, n12=0.20, n13=0.25 * 25000 / 15000, n23=0.25 * 25000 / 15000, G12=25000 / 2.4, G13=6000.0, G23=6000.0)
SHALE_B = dict(E1=40000.0, E2=40000.0, E3=28000.0, n12=0.18, n13=0.22 * 40000 / 28000, n23=0.22 * 40000 / 28000, G12=40000 / 2.36, G13=12000.0, G23=12000.0)
wood_basis = 'README: OrthoWoodCreep = creep of wood with L-T-R directional parameters (Pan et al. 2026)'
rock_basis = 'README: TIRockCreep = transversely isotropic Caney shale (Lu et al., in review); code: z axis normal to bedding'
for fname, kind, coords in [('OrthoWoodCreep_General.for', 'wood', None),
                            ('Ortho_WoodCreep_Cube.for', 'wood', 'ROT=DATAN((COORDS(3)-0.25)/(COORDS(1)-0.25)): local R-T axes rotate with position (growth-ring centre at x=z=0.25 m)'),
                            ('OrthoWoodCreep_Column.for', 'wood', 'XCENTER chosen by COORDS(3) layer (0.04 m steps), ROT=DATAN((COORDS(3)-XC2)/(COORDS(1)-XC1))'),
                            ('TIRockCreep_GENERAL.for', 'rock', None),
                            ('TIRockCreep_CANEY.for', 'rock', 'ISWITCH=18*k chosen by COORDS(3) against depths 82/94/104/140 m: selects which of 5 PROPS blocks is used')]:
    src = 'glu46__3D_anisotropic_viscoelastic_model/' + fname
    layers = 5 if 'CANEY' in fname else 1
    if layers == 1:
        spec = [(i + 1, PN[i]) for i in range(9)]
        exprs = {10: 'PROPS(1+9)', 11: 'PROPS(2+9)', 12: 'PROPS(3+9)', 13: 'PROPS(4+9)', 14: 'PROPS(5+9)', 15: 'PROPS(6+9)', 16: 'PROPS(7+9)', 17: 'PROPS(8+9)', 18: 'PROPS(9+9)'}
        pm = pmap(src, spec) + [dict(index=k, name='N' + PN[k - 10][1:3], code=quote_props(src, k, e)) for k, e in exprs.items()]
    else:
        pm = []
        for L in range(5):
            for i in range(1, 19):
                e = f'PROPS({i}+ISWITCH)' if i <= 9 else f'PROPS({i - 9}+9+ISWITCH)'
                pm.append(dict(index=18 * L + i, name=(PN[i - 1] if i <= 9 else 'N' + PN[i - 10][1:3]) + f' layer{L + 1}', code=quote_props(src, 0, e) + f'  [ISWITCH={18 * L}]'))
    if kind == 'wood':
        sets = [creep_set('A', 'Norway spruce', 'Norway spruce (softwood, 12% MC), axes 1=R 2=L 3=T', SPRUCE, 0.15, 'base set', 'class-typical', layers),
                creep_set('B', 'European beech', 'European beech (hardwood, 12% MC), axes 1=R 2=L 3=T', BEECH, 0.20, 'different species of the same class; creep exponent +33%', 'class-typical', layers)]
        mc, cb = 'wood (orthotropic power-law creep)', wood_basis
    else:
        sets = [creep_set('A', 'Caney-class shale', 'organic-rich shale (Caney class), TI, axis 3 normal to bedding', SHALE_A, 0.03, 'base set', 'class-typical', layers),
                creep_set('B', 'stiffer shale', 'stiffer, less clay-rich shale (Barnett/Haynesville class), TI', SHALE_B, 0.045, 'different shale of the same class; E +60%, creep exponent +50%', 'class-typical', layers)]
        mc, cb = 'shale (transversely isotropic power-law creep)', rock_basis
    flags = ['NSTATV = 20 Kelvin units x 36 = 720 (code comment "NSTATEV=NS_YU*6*6=720")', 'units: code is unit-free in stress; retardation times are hard-coded 1e-6..1e13 (s)']
    if coords:
        flags.append('reads COORDS: ' + coords)
    geo = []
    st = 'covered'
    if 'Cube' in fname:
        geo = [dict(input='experiment geometry', value='single element inside [0,0.5]^3 m (README: wood cube 0.5m x 0.5m x 0.5m); every integration point with |x-0.25| and |z-0.25| bounded away from 0 (e.g. element [0.30,0.40]^3) so ROT=atan((z-0.25)/(x-0.25)) is finite and not 0/0',
                    basis="D-21a (a): Cube may clear R2 via the README-documented geometry; Scout adds the README geometry to the harvest", loading_origin='author_documented_geometry', confidence='author-other-context')]
        st = 'covered_pending_harvest_geometry'
    elif 'Column' in fname:
        st = 'refused_R2_needs_documented_geometry'
        flags.append('D-21a (a): glu46 Column stays refused (needs_documented_geometry); constants kept for completeness, not run')
    elif layers > 1:
        st = 'covered_pending_override'
        for s_ in sets:
            blocks = [[k['value'] for k in sorted(s_['constants'], key=lambda x: x['index'])[18 * L:18 * L + 18]] for L in range(5)]
            assert all(repr(b) == repr(blocks[0]) for b in blocks), 'CANEY layer blocks must be bitwise identical'
        caney_override = [dict(flag='reads_coords_or_noel', proposed=False,
            static_evidence="TIRockCreep_CANEY.for:50-66: COORDS(3) is compared with A1..A4 (82/94/104/140) only to set ISWITCH = 18*k, the offset of the PROPS block read at :74-98; ROT is a constant (0*PI/6); COORDS is not used anywhere else",
            data_evidence='PROPS 1-18, 19-36, 37-54, 55-72, 73-90 are bitwise identical in every set (builder assertion), so every ISWITCH reads the same values',
            dynamic_evidence='pending: run the original with the element at two depths that select different ISWITCH (e.g. z=0..1 and z=200..201) and show identical STRESS/DDSDDE/STATEV',
            status='proposed, needs Vera per D-21a (e)')]
    for s_ in sets:
        s_['non_props_choices'] = geo
    if layers > 1:
        flags.append('CANEY: all 5 layer blocks carry the same set, so the material is position-independent and the COORDS read cannot change the response (only which identical block is read)')
    row(src, material_class=mc, class_basis=cb, unit_system='MPa, s (compliance 1/MPa at t = 1 s)', props_map=pm, sets=sets, nstatv=720,
        nstatv_basis='code comment: "IN TOTAL NSTATEV=NS_YU*6*6=720"; NS_YU=20 (PARAMETER)', initial_statev='code zeroes STATEV when TIME(2) <= 0',
        reads_coords_or_noel=bool(coords), coords_note=coords or 'not read',
        status=st, flags=flags, static_scan_overrides=(caney_override if layers > 1 else ()),
        lookups=[dict(id='L-CREEP-1', source=src, constants='B_ij, n_ij', material_class=mc,
                      what='Pan, Bunger & Lu, IJSS 332 (2026) 113923, doi 10.1016/j.ijsolstr.2026.113923 (paywalled; Scout: NOT FOUND) — B_ij/n_ij for wood and shale', status='answered NOT FOUND; council values stand as class-typical', priority='low')])
    ROWS[-1]['axis_mapping'] = (dict(mapping='1=R, 2=L, 3=T', confidence='interpreted', basis="2 = L supported (README: growth-ring origin at the centre of the T-R plane; ROT rotates about y: 'Y IS IDENTICAL TO Y''); 1 = R and 3 = T inferred from the ROT sign (x' radial at +x of the ring centre), not author-stated (Scout L-CREEP-1)")
                                if kind == 'wood' else dict(mapping='3 = normal to bedding, 1-2 = bedding plane', confidence='author-kept', basis="code comment 'THE Z AXIS IS SET TO BE PERPENDICULAR TO THE BEDDING PLANE'"))

# ---------------------------------------------------------------- thealanjason visco-Ogden (hydrogel)
for src in ['thealanjason__umat_finite_viscoelasticity/UMAT/VISC_OGDEN_1EL.for', 'thealanjason__umat_finite_viscoelasticity/simulation_input_files/VISC_OGDEN_1EL.for']:
    nm = ['MU', 'ALPHA', 'KELAS', 'MUVIS', 'ALPHAVIS', 'KVIS', 'ETADEV', 'ETAVOL']
    pm = pmap(src, [(i + 1, n) for i, n in enumerate(nm)])
    A = [0.004, 2.1474, 40.0, 0.0664, 0.6011, 60.0, 0.0525216, 78.954]
    B = [0.0050, 2.70, 50.0, 0.0414, 0.8837, 78.0, 0.0179706, 29.4715]
    BCH = {0: 'chosen: set A MU +25% (G4: equilibrium moved >= 20%)', 1: 'chosen: set A ALPHA +26%', 2: 'chosen: set A KELAS +25%', 5: 'chosen: set A KVIS +30% (F2, same-material fallback)'}
    units = ['MPa', '-', 'MPa', 'MPa', '-', 'MPa', 'MPa s', 'MPa s']
    sets = [dict(set_id='A', label='hydrogel, 2EL fit, branch 1', material="the author's hydrogel; equilibrium + first relaxation branch of the author's 2EL fit", independence='base set',
                 constants=[c(i + 1, nm[i], A[i], units[i], "author deck simulation_input_files/Uniaxial/2EL/uniaxial_tension/pt06/pt06.inp:57 (first 8 of 13 constants of the author's 2EL fit)", 'author-other-context') for i in range(8)],
                 validity=dict(mu_alpha_gt_0=A[0] * A[1] > 0 and A[3] * A[4] > 0, K_over_mu=A[2] / A[0], tau_dev_s=round(A[6] / A[3], 3), tau_vol_s=round(A[7] / A[5], 3)),
                 activation=f'relaxation time tau_dev = ETADEV/MUVIS = {A[6] / A[3]:.2f} s, inside [0.1,10] x probe period'),
            dict(set_id='B', label='hydrogel, 3EL fit, branch 1', material="the author's hydrogel; equilibrium + first branch of the author's 3EL fit", independence='equilibrium MU/ALPHA/KELAS +25% (chosen); viscous branch from an independent fit: MUVIS -38%, ETADEV -66%, ALPHAVIS +47%',
                 constants=[c(i + 1, nm[i], B[i], units[i], BCH[i], 'chosen') if i in BCH else
                            c(i + 1, nm[i], B[i], units[i], "author deck simulation_input_files/Uniaxial/3EL/uniaxial_tension/pt06/pt06.inp:57 (constants 4,5,7,8 of the author's 3EL fit, first relaxation branch)", 'author-other-context') for i in range(8)],
                 validity=dict(mu_alpha_gt_0=True, K_over_mu=B[2] / B[0], tau_dev_s=round(B[6] / B[3], 3), tau_vol_s=round(B[7] / B[5], 3)),
                 activation=f'tau_dev = {B[6] / B[3]:.2f} s')]
    blocked = 'simulation_input_files' in src
    row(src, material_class='hydrogel (finite viscoelasticity, 1-term Ogden branches)', class_basis="README: 'Implementation of a Viscoelastic Model for Hydrogels in ABAQUS'",
        unit_system='MPa, s (author decks)', props_map=pm, sets=sets, nstatv=6, nstatv_basis='STATEV(1..6) = Be components (VISC_OGDEN_1EL.for:389-394)',
        initial_statev='code sets Be = I (STATEV 1-3 = 1, 4-6 = 0) at KSTEP=1, KINC=1',
        kinc1_statev_reset="IF (KSTEP.EQ.1 .AND. KINC.EQ.1) THEN STATEV(1:3)=1, STATEV(4:6)=0 (:160-165)",
        status='covered_blocked_non_data' if blocked else 'covered',
        flags=["D-21a (c): the author's 2EL/3EL fits are used as council class values, labelled author-other-context, counted only in the council tier (the author states the 1EL model could not be fitted, chap6.tex:4)",
               'near-incompressible (K/mu = 1e4): finite-strain probe'] + (['registry compiled=False for this copy (older revision): compile problem, not data'] if blocked else []))


# ---------------------------------------------------------------- Yutu0k plane-stress elastic (D-21 row; R1 is the alternative)
src = 'Yutu0k__ABQflow/examples/07_SubroutineJob/subroutine/umat_elastic.for'
pm = pmap(src, [(1, 'E'), (2, 'NU')])
A = iso_set('A', 'steel (author README example)', 'structural steel', 210000.0, 0.30, 'MPa',
            "README.md:68 '\"youngs_modulus\": 210000' (usage example of the template; other context)", "author template deck planar_stress_umat_template.inp:3734 '{{youngs_modulus}}, 0.3'", 'author-other-context', 'base set')
A['constants'][1]['confidence'] = 'author-kept'
B = iso_set('B', 'aluminium', ALU[0], ALU[1], ALU[2], 'MPa', 'handbook E of Al alloys (uncited)', 'handbook nu of Al alloys (uncited)', 'class-typical', 'different material of the same class (E -67%, nu +10%)')
row(src, material_class='isotropic linear elastic metal', class_basis="README example 'youngs_modulus': 210000 with the author's plane-stress template deck",
    unit_system='MPa', props_map=pm, sets=[A, B], nstatv=0, nstatv_basis="header comment 'No state variables (NSTATV = 0, no *Depvar needed)'", initial_statev=None,
    family='elasticity', formulation_3d_only='no: NDI=3 (3D/plane strain) and NDI=2 (plane stress, CPS3/CPS4R) branches',
    flags=['registry family label hyperelasticity is wrong: elasticity', 'registry terminal state unsupported_formulation ("no material constants"); the author template deck is plane stress (CPS3/CPS4R, NTENS=3) — the council deck should use plane stress (D-19a R3 CPS4) or 3D; both branches exist',
           'alternative R1 route (author deck + harvest) would need every sweep value 190000/200000/210000 (README/tests) with nu 0.3 to pass; not taken here'])


# ---------------------------------------------------------------- R-3 / R-4 post-pass (amendment 1)
LOOKUPS = json.load(open(ROOT / 'corpus_campaign/material_data/d21_lookups.json'))['lookups']
def lookup_value_names(lid, sub=None):
    L = LOOKUPS[lid][sub] if sub else LOOKUPS[lid]
    v = L.get('values', {})
    names = set(v.keys()) if isinstance(v, dict) else {x['name'] for x in v}
    names |= {x['name'] for x in L.get('also_published_not_requested', [])}
    return names
VERIF_ROWS = ('Hashin', 'vp_leonov', 'vevp_leonov')
VERIF = {}
for n, ln in [('E1', 'E1'), ('E2', 'E2'), ('G12', 'G12'), ('v12', 'nu12'), ('Xt', 'Xt'), ('Xc', 'Xc'), ('Yt', 'Yt'), ('Yc', 'Yc'), ('Sl', 'Sl'),
              ('Gft', 'Gft (G1+)'), ('Gfc', 'Gfc (G1-)'), ('Gmt', 'G2+ (mode I transverse)'), ('Gmc', 'G6 (shear)')]:
    VERIF[('Hashin', 'B', n)] = ('L-HASHIN-1', None, ln)
for t in ('vp_leonov', 'vevp_leonov'):
    VERIF[(t, 'A', 'dH')] = ('L-LEONOV-1', 'iPP', 'dU_II_kJ_per_mol')
    VERIF[(t, 'B', 'dH')] = ('L-LEONOV-1', 'HDPE', 'dU_II_kJ_per_mol')
    VERIF[(t, 'B', 'mu')] = ('L-LEONOV-1', 'HDPE', 'mu')
FALLBACK = ('abuganza', 'thealanjason')
ELASTIC_NAMES = {'lam', 'mu', 'k(bulk)', 'MU', 'ALPHA', 'KELAS'}
for r in ROWS:
    A_, B_ = r['sets'][0], r['sets'][1]
    route = 'same_material_fallback' if any(t in r['source_id'] for t in FALLBACK) else 'different_material'
    B_['g4_route'] = route
    a = {k['index']: k for k in A_['constants']}
    coinc = []
    for k in B_['constants']:
        ka = a[k['index']]
        if k['confidence'] == 'author-kept' and ka['confidence'] == 'author-kept':
            continue                                   # R-2 exempt
        va, vb = ka['value'], k['value']
        rel = abs(vb - va) / max(abs(va), abs(vb)) if (va or vb) else 0.0
        if route == 'same_material_fallback':
            need = 0.2 if k['name'] in ELASTIC_NAMES else 0.3
            # relative move measured against set A
            mv = abs(vb - va) / abs(va) if va else (1.0 if vb else 0.0)
            assert mv >= need - 1e-9, (r['source_id'], k['name'], va, vb, need)
        elif va == vb:
            coinc.append(k['name'])
    if route == 'different_material':
        B_['coinciding_constants'] = coinc            # for Vera: must be genuinely shared class values, never mechanism constants
for r in ROWS:
    for s_ in r['sets']:
        for k in s_['constants']:
            b = k['basis']
            if 'sibling' in b and k['confidence'] == 'chosen':
                k['confidence'] = 'author-other-context'            # R-3: the author's value from another routine/deck
            if re.search(r'EC2|MC2010|EN 1992', b):
                k['confidence'] = 'looked-up'; k['verification_pending'] = 'Scout L-EC2-1 (R-4: stands only once verified)'
            key = VERIF.get((next((t for t in VERIF_ROWS if t in r['source_id']), None), s_['set_id'], k['name']))
            if key:
                lid, sub, lname = key
                assert lname in lookup_value_names(lid, sub), (r['source_id'], k['name'], key)
                k['verification'] = 'verified by Scout: d21_lookups.json ' + lid + ('/' + sub if sub else '') + ' value ' + repr(lname)
            elif k['name'] in ('E1MP', 'E2MP') and 'NONLIPLS' in r['source_id']:
                k['verification_note'] = 'Scout quoted the source in L-CART-1 sources[] (that lookup has no values list, so no verification field is set)'
            assert not (k['confidence'] == 'class-typical' and re.search(r'et al|Table|EC2|MC2010', b)), (r['source_id'], k)

for r in ROWS:   # F1: 'verification' only from VERIF, i.e. only for names in the lookup's values
    for s_ in r['sets']:
        for k in s_['constants']:
            if 'verification' in k:
                assert k['verification'].startswith('verified by Scout: d21_lookups.json ') and any(t in r['source_id'] for t in VERIF_ROWS), (r['source_id'], k)

# ---------------------------------------------------------------- amendment 2: council formulation statements (D-21b; code evidence quoted)
FORMULATION = {
    'artorg-unibe-ch__HFE/02_CODE/abq/UMAT_BIPHASIC.f': ('3D', 'C3D8 (NTENS=6), NLGEOM as recorded', [
        'UMAT_BIPHASIC.f:690 "DO K1 = 1,6" (return-mapping loop over the NTENS-dimensioned residual RR)',
        'UMAT_BIPHASIC.f:986-987 "DO K1 = 1,6 / STATEV(8+K1) = SS1(K1)" (SDV 9-14 NOMINAL STRESS VECTOR, 6 components)',
        'UMAT_BIPHASIC.f:1066-1074 STATEV(23..31) = DFGRD1(1..3,1..3)']),
    'simoneponcioni__HFE/02_CODE/abq/UMAT_BIPHASIC.f': ('3D', 'C3D8 (NTENS=6), NLGEOM as recorded', [
        'UMAT_BIPHASIC.f:691 "DO K1 = 1,6"', 'UMAT_BIPHASIC.f:987-988 "DO K1 = 1,6 / STATEV(8+K1) = SS1(K1)"',
        'UMAT_BIPHASIC.f:1067-1075 STATEV(23..31) = DFGRD1(1..3,1..3)']),
    'marioruiarruda__Hashin_3D_UMAT/umat_hashin3D_f90.f90': ('3D', 'C3D8 (NDI=3, NTENS=6)', [
        'umat_hashin3D_f90.f90:16 "UMAT 2D AND 3D ELEMENTS WITH HASHIN LINEAR DAMAGE"',
        'umat_hashin3D_f90.f90:190 "if (ndi==3) then !!!! FOR 3D ANALYSIS" (also :269, :293, :348, :395); the 3D branch is chosen, the 2D branch is not exercised']),
    'marioruiarruda__Mazars_UMAT/umat_mazars_f90.f90': ('3D', 'C3D8 (NDI=3, NTENS=6)', [
        'umat_mazars_f90.f90:150 "if (ndi==3) then ! FOR 3D SOLID ANALYSIS" / :154 "else ! FOR 2D PLANE ANALYSIS"',
        'umat_mazars_f90.f90:411 "if (ndi==3) then ! FOR 3D SOLID ANALYSIS" with Cij(6,6) at :424; the 3D branch is chosen']),
    'baw-de__poroMechanicalFoam/abaqusUMATs/abaqusUmatMohrCoulomb/MohrCoulombAbaqus.for': ('3D', 'C3D8 (NTENS=6)', [
        'MohrCoulombAbaqus.for:267-269 "Plane situations (plane stress, plane strain and axisymmetry): Sigma = [sig_x sig_y sig_z tau_xy] ... General 3D: Sigma = [sig_x sig_y sig_z tau_xy tau_xz tau_yz]"',
        'MohrCoulombAbaqus.for:203 "call MohrCoulombStressReturn(SigB,NTENS,...)" and :410 / :1019 "if (nsigma == 4) then" (4-component branch); NTENS=6 general-3D path chosen']),
    'RafalMichalczyk__PavementDesign/Subroutines/umat_ms_plast.for': ('3D', 'C3D8 (NTENS=6 only)', [
        'umat_ms_plast.for:64-67 "do i=1, 3 / devstraininc(i)=dstran(i)-volstraininc / devstraininc(i+3)=dstran(i+3)" (6 components hard-coded)',
        'umat_ms_plast.for:120-126 "stress(i+3) = stress(i+3)+ 2.*xg*(...)" for i=1..3', 'umat_ms_plast.for:136-137 "... devstressnew(5)**2+devstressnew(6)**2"']),
    'bessagroup__f3dasm_simulate/src/f3dasm_simulate/abaqus/scriptbase/benchmark_abaqus_scripts/vp_leonov_model.f': ('3D', 'C3D8 (NTENS=6), NLGEOM=YES', [
        'vp_leonov_model.f:314 "if (NTENS == 4) then" (plane strain/axisymmetric branch, shear 13/23 set to zero) ... :322-328 else branch uses Strain(5), Strain(6): NTENS=6 3D path chosen']),
    'bessagroup__f3dasm_simulate/src/f3dasm_simulate/abaqus/scriptbase/benchmark_abaqus_scripts/vevp_leonov_model.f': ('3D', 'C3D8 (NTENS=6), NLGEOM=YES', [
        'vevp_leonov_model.f:583 "if (NTENS == 4) then" ... :597 else branch "eTrialStrain(2,3) = Strain(6) + DStrain(6)/ R2": NTENS=6 3D path chosen']),
    'glu46__3D_anisotropic_viscoelastic_model/OrthoWoodCreep_General.for': ('3D', 'C3D8 (NTENS=6 only)', [
        'OrthoWoodCreep_General.for:275-277 "DO I = 1, 6 / DO J = 1,6 / YU_IN(KMU,I,J) = STATEV(K1)" (6x6 hard-coded state)',
        'OrthoWoodCreep_General.for:53 "XMATD(6,6) = PROPS(4)" and TRANSFORM_T(1..6,6) at :144-149 on NTENS-dimensioned arrays', 'repository name "3D_anisotropic_viscoelastic_model"']),
    'glu46__3D_anisotropic_viscoelastic_model/TIRockCreep_GENERAL.for': ('3D', 'C3D8 (NTENS=6 only)', [
        'TIRockCreep_GENERAL.for:270-272 "DO I = 1, 6 / DO J = 1,6 / YU_IN(KMU,I,J) = STATEV(K1)"',
        'TIRockCreep_GENERAL.for:50 "XMATD(6,6) = PROPS(4)" and TRANSFORM_T(1..6,6) at :139-144', 'repository name "3D_anisotropic_viscoelastic_model"']),
}
for r in ROWS:
    if r['source_id'] in FORMULATION:
        st, el, ev = FORMULATION[r['source_id']]
        r['formulation'] = dict(statement=st, element=el, evidence=ev, origin='council_choice',
                                ref='corpus_campaign/material_data/d21_rule_amendment_2.json')

# ---------------------------------------------------------------- write
OUT.write_text(''.join(json.dumps(r, sort_keys=False) + '\n' for r in ROWS))
print(len(ROWS), 'rows')
for r in ROWS:
    bad = [s['set_id'] for s in r['sets'] if not all(v is not False for v in s['validity'].values() if isinstance(v, bool))]
    print(r['status'].ljust(26), r['family'][:22].ljust(22), len(r['sets']), 'sets', 'INVALID:' + str(bad) if bad else '', r['source_id'])
