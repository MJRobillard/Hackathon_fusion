# Visualization System Improvements

## Issues Fixed

### 1. Charts Not Showing
**Problem**: Charts weren't displaying because:
- `activeRunId` wasn't being passed correctly from query results
- Data flow from backend to frontend wasn't complete
- Missing API integration

**Solutions Implemented**:
- Added `/api/v1/runs/similar/{run_id}` endpoint for finding similar experiments
- Improved AnalyticsPanel to fetch runs from database
- Added proper data fetching with React Query
- Fixed prop flow from parent component

### 2. MongoDB Similarity Matching
**Problem**: Need intelligent way to find similar experiments based on:
- Geometry type
- Enrichment percentage (within ±1%)
- Temperature (within ±100K)
- Material composition

**Solution**: Created similarity scoring algorithm:
- Geometry match: 10 points (exact match)
- Enrichment proximity: up to 5 points (decreases with distance)
- Temperature proximity: up to 3 points (decreases with distance)
- Results sorted by similarity score

### 3. Data Flow Improvements
**Changes Made**:
- AnalyticsPanel now fetches all runs from `/api/v1/runs`
- Similar runs shown when viewing a single run
- All runs displayed in dashboard view
- Click handlers ready for run selection (needs parent callback)

## API Endpoints Added

### `/api/v1/runs/similar/{run_id}?limit=10`
Finds similar runs based on specification parameters.

**Response**:
```json
{
  "reference_run_id": "run_abc123",
  "similar_runs": [
    {
      "run_id": "run_def456",
      "geometry": "PWR pin cell",
      "enrichment_pct": 4.5,
      "temperature_K": 600,
      "keff": 1.00234,
      "keff_std": 0.00012,
      ...
    }
  ],
  "total_found": 5
}
```

## Similarity Algorithm

The similarity score is calculated as:
1. **Geometry Match** (10 points): Exact match on geometry name
2. **Enrichment Proximity** (0-5 points): 
   - Formula: `max(0, 5.0 - abs(diff) * 2)`
   - 0% difference = 5 points
   - 2.5% difference = 0 points
3. **Temperature Proximity** (0-3 points):
   - Formula: `max(0, 3.0 - (abs(diff)/100) * 1.5)`
   - 0K difference = 3 points
   - 200K difference = 0 points

Runs are sorted by total score (highest first).

## Next Steps

To complete the integration:
1. Add parent callback in `page.tsx` to handle run selection from AnalyticsPanel
2. Ensure `activeQuery.results.run_id` is populated when queries complete
3. Consider adding material composition matching to similarity algorithm
4. Add filters for similarity search (exact geometry only, etc.)

