export const TIER = { LEVERS: 1, ASSUMPTIONS: 2, REFERENCE: 3 };

export const GROUPS = [
    {
        id: 'taxes',
        title: 'Taxes',
        icon: 'fa-percent',
        tier: TIER.LEVERS
    },
    {
        id: 'spending',
        title: 'Government spending & pensions',
        icon: 'fa-bank',
        tier: TIER.LEVERS
    },
    {
        id: 'production',
        title: 'Growth & production',
        icon: 'fa-line-chart',
        tier: TIER.LEVERS
    },
    {
        id: 'households',
        title: 'Households & preferences',
        icon: 'fa-user',
        tier: TIER.ASSUMPTIONS
    },
    {
        id: 'demographics',
        title: 'Demographics',
        icon: 'fa-users',
        tier: TIER.ASSUMPTIONS
    },
    {
        id: 'open',
        title: 'Open economy',
        icon: 'fa-globe',
        tier: TIER.ASSUMPTIONS
    },
    {
        id: 'arrays',
        title: 'Arrays & reference data',
        icon: 'fa-table',
        tier: TIER.REFERENCE
    },
    {
        id: 'advanced',
        title: 'Advanced',
        icon: 'fa-cogs',
        tier: TIER.REFERENCE
    }
];

export const DEFAULT_GROUP = 'advanced';

export const SUFFIX_RULES = [
    { suffix: '_preTP', group: 'arrays', reason: 'calibration' },
    { suffix: '_ge', group: 'arrays', reason: 'calibration' }
];

export function suffixRule(name){
    for (let i = 0; i < SUFFIX_RULES.length; i++){
        let rule = SUFFIX_RULES[i];
        if (String(name).slice(-rule.suffix.length) == rule.suffix){
            return rule;
        }
    }
    return null;
}

export const GROUP_OF = {
    cit_rate: 'taxes',
    tau_payroll: 'taxes',
    frac_tax_payroll: 'taxes',
    inv_tax_credit: 'taxes',
    c_corp_share_of_assets: 'taxes',
    tau_bq: 'taxes',
    tau_c: 'taxes',
    p_wealth: 'taxes',
    h_wealth: 'taxes',
    m_wealth: 'taxes',
    tax_func_type: 'taxes',
    labor_income_tax_noncompliance_rate: 'taxes',
    capital_income_tax_noncompliance_rate: 'taxes',
    adjustment_factor_for_cit_receipts: 'taxes',
    delta_tau_annual: 'taxes',
    etr_params: 'taxes',
    mtrx_params: 'taxes',
    mtry_params: 'taxes',
    income_tax_filer: 'taxes',
    wealth_tax_filer: 'taxes',
    zero_taxes: 'taxes',
    constant_rates: 'taxes',
    analytical_mtrs: 'taxes',
    age_specific: 'taxes',

    alpha_G: 'spending',
    alpha_T: 'spending',
    alpha_I: 'spending',
    infra_investment_leakage_rate: 'spending',
    ubi_nom_017: 'spending',
    ubi_nom_1864: 'spending',
    ubi_nom_65p: 'spending',
    ubi_nom_max: 'spending',
    ubi_growthadj: 'spending',
    tau_p: 'spending',
    retirement_age: 'spending',
    pension_system: 'spending',
    initial_debt_ratio: 'spending',
    debt_ratio_ss: 'spending',
    initial_Kg_ratio: 'spending',
    tG1: 'spending',
    tG2: 'spending',
    rho_G: 'spending',
    budget_balance: 'spending',
    baseline_spending: 'spending',
    alpha_bs_G: 'spending',
    alpha_bs_I: 'spending',
    alpha_bs_T: 'spending',
    alpha_FA: 'spending',
    replacement_rate_adjust: 'spending',
    baseline_theta: 'spending',
    AIME_bkt_1: 'spending',
    AIME_bkt_2: 'spending',
    PIA_rate_bkt_1: 'spending',
    PIA_rate_bkt_2: 'spending',
    PIA_rate_bkt_3: 'spending',
    PIA_minpayment: 'spending',
    PIA_maxpayment: 'spending',
    alpha_db: 'spending',
    yr_contrib: 'spending',
    indR: 'spending',
    k_ret: 'spending',
    vpoint: 'spending',
    avg_earn_num_years: 'spending',

    g_y_annual: 'production',
    g_y: 'production',
    gamma: 'production',
    gamma_g: 'production',
    Z: 'production',
    epsilon: 'production',
    delta_annual: 'production',
    delta_g_annual: 'production',
    io_matrix: 'production',
    alpha_c: 'production',

    sigma: 'households',
    frisch: 'households',
    beta_annual: 'households',
    chi_b: 'households',
    chi_n: 'households',
    ltilde: 'households',
    lambdas: 'households',
    e: 'households',
    zeta: 'households',
    eta: 'households',
    eta_RM: 'households',
    use_zeta: 'open',
    alpha_RM_1: 'open',
    alpha_RM_T: 'open',
    g_RM: 'open',
    constant_demographics: 'households',

    start_year: 'demographics',
    g_n_ss: 'demographics',
    g_n: 'demographics',
    omega: 'demographics',
    omega_SS: 'demographics',
    omega_S_preTP: 'demographics',
    imm_rates: 'demographics',
    rho: 'demographics',
    initial_pop: 'demographics',

    world_int_rate_annual: 'open',
    zeta_D: 'open',
    zeta_K: 'open',
    initial_foreign_debt_ratio: 'open',
    foreign_debt_ratio: 'open',
    r_gov_shift: 'open',
    r_gov_scale: 'open',
    r_gov_DY: 'open',
    r_gov_DY2: 'open',

    S: 'advanced',
    J: 'advanced',
    T: 'advanced',
    I: 'advanced',
    M: 'advanced',
    starting_age: 'advanced',
    ending_age: 'advanced',
    nu: 'advanced',
    maxiter: 'advanced',
    mindist_SS: 'advanced',
    mindist_TPI: 'advanced',
    RC_SS: 'advanced',
    RC_TPI: 'advanced',
    SS_root_method: 'advanced',
    FOC_root_method: 'advanced',
    initial_guess_r_SS: 'advanced',
    initial_guess_TR_SS: 'advanced',
    initial_guess_factor_SS: 'advanced',
    initial_guess_w_SS: 'advanced',
    use_sparse_FOC_jac: 'advanced'
};

export const PARAMETER_POLICY = {
    chi_n: { reason: 'calibration' },
    e: { reason: 'calibration' },
    zeta: { reason: 'calibration' },
    eta: { reason: 'calibration' },
    eta_RM: { reason: 'calibration' },
    omega: { reason: 'calibration' },
    omega_SS: { reason: 'calibration' },
    omega_S_preTP: { reason: 'calibration' },
    imm_rates: { reason: 'calibration' },
    rho: { reason: 'calibration' },
    g_n: { reason: 'calibration' },
    g_y: { reason: 'calibration' },
    initial_pop: { reason: 'calibration' },
    io_matrix: { reason: 'calibration' },
    alpha_c: { reason: 'calibration' },
    etr_params: { reason: 'estimated' },
    mtrx_params: { reason: 'estimated' },
    mtry_params: { reason: 'estimated' },
    S: { reason: 'structural' },
    J: { reason: 'structural' },
    T: { reason: 'structural' },
    I: { reason: 'structural' },
    M: { reason: 'structural' },
    starting_age: { reason: 'structural' },
    ending_age: { reason: 'structural' },
    nu: { reason: 'solver' },
    maxiter: { reason: 'solver' },
    mindist_SS: { reason: 'solver' },
    mindist_TPI: { reason: 'solver' },
    RC_SS: { reason: 'solver' },
    RC_TPI: { reason: 'solver' },
    SS_root_method: { reason: 'solver' },
    FOC_root_method: { reason: 'solver' },
    initial_guess_r_SS: { reason: 'solver' },
    initial_guess_TR_SS: { reason: 'solver' },
    initial_guess_w_SS: { reason: 'solver' },
    initial_guess_factor_SS: { reason: 'solver' },
    use_sparse_FOC_jac: { reason: 'solver' }
};

export const DIMENSION = {
    beta_annual: 'by_j',
    lambdas: 'by_j',
    chi_b: 'by_j',
    capital_income_tax_noncompliance_rate: 'by_j',
    income_tax_filer: 'by_j',
    labor_income_tax_noncompliance_rate: 'by_j',
    wealth_tax_filer: 'by_j',
    chi_n: 'by_age',
    omega_SS: 'by_age',
    omega_S_preTP: 'by_age',
    e: 'matrix',
    zeta: 'matrix',
    eta: 'matrix',
    eta_RM: 'matrix',
    io_matrix: 'matrix',
    omega: 'matrix',
    etr_params: 'matrix',
    mtrx_params: 'matrix',
    mtry_params: 'matrix'
};

export const CONSTRAINT = {
    lambdas: 'sum_to_one'
};

export const CHOICES = {
    pension_system: [
        'US-Style Social Security',
        'Defined Benefits',
        'Notional Defined Contribution',
        'Points System'
    ],
    SS_root_method: ['hybr', 'lm', 'krylov', 'anderson', 'df-sane'],
    FOC_root_method: ['hybr', 'lm', 'krylov', 'anderson', 'df-sane'],
    tax_func_type: ['DEP', 'DEP_totalinc', 'GS', 'HSV', 'linear', 'mono', 'mono2D']
};

export const LOCKED_DIMS = ['S', 'T', 'J', 'M', 'I'];
export const BINARY_ROWS = ['income_tax_filer', 'wealth_tax_filer'];

export const TABLE_AXES = {
    e: { row: 'Age', column: 'Lifetime-income group' },
    eta: { row: 'Age', column: 'Lifetime-income group' },
    eta_RM: { row: 'Age', column: 'Lifetime-income group' },
    zeta: { row: 'Age', column: 'Lifetime-income group' },
    imm_rates: { row: 'Model period', column: 'Age' },
    omega: { row: 'Model period', column: 'Age' },
    rho: { row: 'Model period', column: 'Age' },
    io_matrix: { row: 'Consumption good', column: 'Production good' }
};

function valueDimensions(value){
    let out = [];
    while (Array.isArray(value)){
        out.push(value.length);
        value = value.length ? value[0] : null;
    }
    return out;
}

function allSingleton(dimensions){
    return dimensions.length > 1 && dimensions.every(size => size == 1);
}

export function decorate(name, entry) {
    entry = entry || {};
    let policy = PARAMETER_POLICY[name] || null;
    let ro = policy && (policy.reason == 'structural' || policy.reason == 'solver')
        ? policy
        : null;
    let expertReason = policy && !ro ? policy.reason : null;
    if (!ro && entry.section == 'Model Solution Parameters'){
        ro = { reason: 'solver' };
    }
    let rule = ro ? null : suffixRule(name);
    if (rule){
        expertReason = rule.reason;
    }
    let dimension = DIMENSION[name] || null;
    let dimensions = entry.dimensions || valueDimensions(entry.default);
    let storageShape = null;
    if (allSingleton(dimensions)){
        storageShape = 'singleton_tensor';
        dimension = dimensions.length == 2 && /set value for base year/i.test(entry.description || '')
            ? 'by_year'
            : 'scalar';
    }else if (entry.shape == 'time_x_industry'
        && dimensions.length == 2 && dimensions[1] == 1){
        storageShape = 'column_matrix';
        dimension = 'by_year';
    }else if (!dimension) {
        if (entry.shape == 'scalar'){
            dimension = 'scalar';
        }else if (entry.shape == 'time_x_industry'){
            dimension = 'matrix';
        }else{
            dimension = 'by_year';
        }
    }
    let large = entry.large === true || entry.default === null;
    let tableEditable = dimension == 'by_age' || dimension == 'matrix';
    let access = 'edit';
    if (ro){
        access = 'view';
    }else if (expertReason && tableEditable){
        access = 'expert-edit';
    }else if (large && storageShape != 'column_matrix' && !tableEditable){
        access = 'view';
    }
    return {
        name: name,
        title: entry.title || name,
        description: entry.description || '',
        section: entry.section || '',
        subsection: entry.subsection || null,
        type: entry.type || 'level',
        datatype: entry.datatype || null,
        shape: entry.shape || 'scalar',
        dimension: dimension,
        min: (entry.min === 0 || entry.min) ? entry.min : null,
        max: (entry.max === 0 || entry.max) ? entry.max : null,
        def: entry.default,
        large: large,
        preview: entry.preview || null,
        dimensions: dimensions.length ? dimensions : null,
        storageShape: storageShape,
        tableEditable: tableEditable,
        access: access,
        readOnly: access == 'view',
        readOnlyReason: access == 'view' ? (ro ? ro.reason : 'calibration') : null,
        expertEditReason: access == 'expert-edit' ? expertReason : null,
        binaryRow: BINARY_ROWS.indexOf(name) >= 0,
        axes: TABLE_AXES[name] || null,
        constraint: CONSTRAINT[name] || null,
        choices: entry.choices || CHOICES[name] || null,
        group: GROUP_OF[name] || (rule ? rule.group : null) || DEFAULT_GROUP
    };
}
