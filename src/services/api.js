/**
 * Synora API Service
 *
 * React frontend -> FastAPI backend adapter.
 *
 * This file intentionally preserves the function names exposed by
 * mockEngine.js so existing views can be migrated with minimal changes.
 */

const API_BASE =
    import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';


// -----------------------------------------------------------------------------
// Generic request helper
// -----------------------------------------------------------------------------

async function request(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            ...(options.body instanceof FormData
                ? {}
                : { 'Content-Type': 'application/json' }),
            ...(options.headers || {}),
        },
    });

    if (!response.ok) {
        let message = `API request failed (${response.status})`;

        try {
            const errorData = await response.json();

            message =
                errorData?.detail ||
                errorData?.error ||
                errorData?.message ||
                message;
        } catch {
            // Response was not JSON.
        }

        const error = new Error(message);
        error.status = response.status;
        throw error;
    }

    const contentType =
        response.headers.get('content-type') || '';

    if (contentType.includes('application/json')) {
        return response.json();
    }

    return response;
}


// -----------------------------------------------------------------------------
// Health
// -----------------------------------------------------------------------------

export async function checkBackendHealth() {
    return request('/api/health');
}


// -----------------------------------------------------------------------------
// Dataset DNA
// -----------------------------------------------------------------------------

/**
 * Fetch the currently loaded source dataset profile.
 *
 * If no dataset has been uploaded yet, the backend uses the configured
 * demonstration dataset.
 */
export async function getDatasetDNA() {
    return request('/api/profile', {
        method: 'POST',
        body: JSON.stringify({}),
    });
}


/**
 * Upload a CSV/XLSX dataset to Synora.
 */
export async function uploadDataset(file) {
    if (!file) {
        throw new Error('No dataset file was provided.');
    }

    const formData = new FormData();
    formData.append('file', file);

    return request('/api/profile', {
        method: 'POST',
        body: formData,
    });
}


// -----------------------------------------------------------------------------
// Feasibility Gate
// -----------------------------------------------------------------------------

/**
 * Evaluate whether a requested cohort is supported by the source dataset.
 *
 * Example:
 *
 * evaluateFeasibility(
 *   {
 *     diabetic: 1,
 *     age_min: 66,
 *     age_max: 90,
 *     gender: 'All',
 *     ethnicity: 'Other'
 *   },
 *   false
 * )
 */
export async function evaluateFeasibility(
    filters = {},
    researcherConfirmed = false
) {
    return request('/api/feasibility', {
        method: 'POST',
        body: JSON.stringify({
            filters,
            researcher_confirmed: researcherConfirmed,
        }),
    });
}


// -----------------------------------------------------------------------------
// Synthetic Generation
// -----------------------------------------------------------------------------

/**
 * Generate a synthetic cohort using the real Python/SDV backend.
 *
 * The backend supports:
 *   - Gaussian Copula
 *   - CTGAN
 *
 * The returned object contains:
 *   - synthPatients
 *   - synthRecords
 *   - trustReport
 *   - certificate
 */
export async function generateSyntheticCohort(config = {}) {
    return request('/api/generate', {
        method: 'POST',
        body: JSON.stringify(config),
    });
}


// -----------------------------------------------------------------------------
// Population Explorer
// -----------------------------------------------------------------------------

export async function getPopulationExplorerData() {
    return request('/api/population');
}


// -----------------------------------------------------------------------------
// Trust Report
// -----------------------------------------------------------------------------

export async function getTrustReport() {
    return request('/api/trust-report');
}


// -----------------------------------------------------------------------------
// Privacy Certificate
// -----------------------------------------------------------------------------

export async function getCertificate() {
    return request('/api/certificate');
}


// -----------------------------------------------------------------------------
// Export
// -----------------------------------------------------------------------------

/**
 * Download:
 *
 *   synthetic_cohort.csv
 *   synthetic_cohort.xlsx
 *   privacy_certificate.json
 *
 * bundled into a single ZIP.
 */
export async function downloadExport(
    researcherConfirmed = false
) {
    const response = await fetch(
        `${API_BASE}/api/export?confirmed=${researcherConfirmed ? 'true' : 'false'}`
    );

    if (!response.ok) {
        let message = `Export failed (${response.status})`;

        try {
            const errorData = await response.json();

            message =
                errorData?.detail ||
                errorData?.error ||
                message;
        } catch {
            // Ignore non-JSON error response.
        }

        throw new Error(message);
    }

    const blob = await response.blob();

    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');

    anchor.href = url;
    anchor.download = 'synora_certified_synthetic_cohort.zip';

    document.body.appendChild(anchor);
    anchor.click();

    anchor.remove();
    window.URL.revokeObjectURL(url);

    return {
        status: 'ok',
        filename: 'synora_certified_synthetic_cohort.zip',
    };
}


// -----------------------------------------------------------------------------
// Compatibility helpers
// -----------------------------------------------------------------------------

/**
 * The old mock engine returned patients and records separately.
 *
 * These helpers make the transition easier for existing components.
 */

export async function getSyntheticPatients() {
    const population = await getPopulationExplorerData();
    return population?.patients || [];
}


export async function getSyntheticRecords() {
    const population = await getPopulationExplorerData();
    return population?.records || [];
}


// -----------------------------------------------------------------------------
// Default export
// -----------------------------------------------------------------------------

const synoraApi = {
    checkBackendHealth,
    getDatasetDNA,
    uploadDataset,
    evaluateFeasibility,
    generateSyntheticCohort,
    getPopulationExplorerData,
    getTrustReport,
    getCertificate,
    downloadExport,
    getSyntheticPatients,
    getSyntheticRecords,
};

export default synoraApi;