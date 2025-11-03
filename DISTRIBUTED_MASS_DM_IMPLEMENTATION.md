# Smart Distribution of Mass DM Across Multiple Accounts

## Overview
Implemented a comprehensive feature that allows users to distribute mass direct messages across multiple Telegram accounts in parallel, significantly reducing execution time and distributing risk.

## Key Features
- **Automatic Distribution**: Users upload a CSV with target user IDs and select multiple accounts
- **Even Distribution**: System automatically splits users evenly across selected accounts
- **Parallel Execution**: Each account processes its batch independently through the worker queue
- **Batch Tracking**: Parent job tracks all child batch jobs for monitoring
- **Smart Remainder Handling**: Last account receives any remainder users to ensure 100% coverage
- **10x Speedup**: 10 accounts means 10x faster completion compared to sequential processing

## Database Changes

### New Job Model Fields
Added to `models.py`:
- `parent_job_id`: Foreign key to link batch jobs to parent distribution job
- `batch_number`: Which batch this job represents (1-indexed)
- `total_batches`: Total number of batches for the distribution
- `batch_user_ids`: JSON array of user IDs assigned to this batch

### Migration
File: `backend/alembic/versions/batch_distribution_migration.py`
- Creates foreign key relationship for batch tracking
- Handles rollback gracefully

## Backend Implementation

### Distribution Service
File: `backend/mass_dm_account/distribution_service.py`

**Key Function**: `distribute_users_across_accounts()`
- Validates all accounts belong to user and are active
- Calculates optimal batch size: `total_users / num_accounts`
- Creates parent job for tracking
- Creates child batch jobs with pre-assigned user IDs
- Ensures even distribution with remainder handling

**Example**:
- 10,000 users, 10 accounts → 1,000 users per account
- 10,000 users, 10 accounts (with remainder) → 999, 999, ..., 1009 (last account)

### API Endpoint
File: `backend/mass_dm_account/router.py`

**Route**: `POST /api/mass-dm-account/create-distributed-job`

**Parameters**:
- `message`: Message to send
- `account_ids`: JSON array of account IDs to distribute across (minimum 2)
- `csv_file`: CSV file with user_id or username columns
- `image_file`: Optional image attachment
- `stop_after_hours`: Optional time limit
- `rate_limit_per_hour`: Rate limiting per account
- `delay_seconds` or `min/max_delay_seconds`: Delay between messages

**Response**:
```json
{
  "success": true,
  "message": "Created 5 distributed Mass DM jobs",
  "job_ids": [101, 102, 103, 104, 105],
  "total_users": 5000,
  "num_accounts": 5,
  "users_per_batch": 1000,
  "distribution_summary": {
    "total_users": 5000,
    "total_accounts": 5,
    "users_per_account": 1000,
    "last_account_users": 1000
  }
}
```

### Task Updates
File: `backend/mass_dm_account/tasks.py`

**Updated `_mass_dm_runner()`**:
- Checks for `job.batch_user_ids` first
- If present, uses the pre-assigned batch instead of reading CSV
- Logs batch information: "Batch 2/5 - 1000 users"
- Falls back to CSV reading for traditional jobs
- Ensures backward compatibility

## Frontend Implementation

### New Page
File: `frontend/src/pages/MassDMDistributed.tsx`

**Features**:
- Multi-select dropdown for account selection (minimum 2 required)
- CSV file upload with live preview
- Real-time distribution preview:
  - Total users from CSV
  - Number of selected accounts
  - Users per account calculation
  - Last account user count
  - "~5x faster" speedup indicator
- Optional image upload
- All standard mass DM options (rate limit, delays, etc.)
- Side-by-side form and preview layout

### Routes
- Route path: `/mass-dm-distributed`
- Added to `frontend/src/App.tsx`
- Added to navigation menu in `frontend/src/components/layout/Layout.tsx`
- Marked as "NEW" in the UI

### Navigation
- Icon: Speed icon (⚡)
- Plan: PRO and ENTERPRISE
- Label: "Distributed Mass DM"

## How It Works

### User Flow

1. **Create Distribution**
   - User navigates to "Distributed Mass DM" page
   - Selects 2+ accounts from dropdown
   - Uploads CSV with user IDs
   - Enters message text and optional settings
   - Sees real-time preview of distribution
   - Clicks "Create Distributed Mass DM"

2. **Backend Processing**
   - Validates accounts and CSV
   - Calls `distribute_users_across_accounts()`
   - Creates parent job
   - Creates 5 child jobs (for 5 accounts):
     - Job 1: Account A, users 1-1000
     - Job 2: Account B, users 1001-2000
     - Job 3: Account C, users 2001-3000
     - Job 4: Account D, users 3001-4000
     - Job 5: Account E, users 4001-5000
   - Enqueues all jobs to worker pool

3. **Parallel Execution**
   - 5 workers process jobs simultaneously
   - Each worker sends messages according to its batch
   - Progress tracked independently per batch
   - All complete in ~1/5 the time

4. **Monitoring**
   - User views "Jobs" page
   - Sees 5 separate jobs with batch info
   - Monitors progress for each batch
   - Parent job tracks overall progress

### Data Flow

```
[User Input] → [API Endpoint]
                   ↓
           [Validation + CSV Parse]
                   ↓
           [Distribution Service]
                   ↓
        [Create Parent Job + Batch Jobs]
                   ↓
         [Enqueue All Jobs to Workers]
                   ↓
    [5 Workers Process in Parallel]
                   ↓
         [Update Job Progress]
                   ↓
        [User Monitors via Jobs Page]
```

## Example Scenarios

### Scenario 1: Small Distribution (5 users, 2 accounts)
- Account A: User 1, 2
- Account B: User 3, 4, 5
- Speedup: ~2x

### Scenario 2: Large Distribution (10,000 users, 10 accounts)
- Each account: ~1,000 users
- Speedup: ~10x
- Estimated time: 
  - Sequential: 10,000 messages × 60s = 166 minutes
  - Distributed: 1,000 messages × 60s = 16 minutes (10x faster!)

### Scenario 3: With Rate Limiting (5,000 users, 5 accounts, 20 msg/hr limit)
- Each account sends max 20 messages per hour
- Job naturally spreads out due to rate limits
- Risk distributed across 5 accounts

## Benefits

✅ **Speed**: Reduces execution time proportionally (10 accounts = 10x faster)
✅ **Risk Distribution**: Spreads send volume across accounts, reducing ban risk
✅ **Automatic**: System handles all distribution math automatically
✅ **Monitoring**: Track each batch independently via Jobs page
✅ **Flexible**: Works with any number of accounts (2+)
✅ **Safe**: Each account has independent rate limiting and delays
✅ **Backward Compatible**: Old single-account Mass DM still works

## Technical Details

### Architecture
- **Distribution happens at creation time** (not runtime)
- **Each batch is an independent job** with its own task
- **Parent job serves for tracking** and reporting
- **CSV is parsed once** and distributed to jobs
- **Workers process independently** in parallel

### Database Relationships
```
User
 └─ Job (parent_job_id=NULL)
     ├─ Job (parent_job_id=parent, batch_number=1)
     ├─ Job (parent_job_id=parent, batch_number=2)
     ├─ Job (parent_job_id=parent, batch_number=3)
     ├─ Job (parent_job_id=parent, batch_number=4)
     └─ Job (parent_job_id=parent, batch_number=5)
```

### File Storage
- Uploaded CSV stored once per job creation
- Same config applied to all batch jobs
- Optional image shared across all batches
- User IDs stored as JSON in `batch_user_ids` field

## Files Modified/Created

### Backend
✅ `models.py` - Added batch distribution fields
✅ `backend/alembic/versions/batch_distribution_migration.py` - Database migration
✅ `backend/mass_dm_account/distribution_service.py` - Distribution logic (NEW)
✅ `backend/mass_dm_account/router.py` - Added `/create-distributed-job` endpoint
✅ `backend/mass_dm_account/tasks.py` - Updated to handle batch user IDs

### Frontend
✅ `frontend/src/pages/MassDMDistributed.tsx` - New page (NEW)
✅ `frontend/src/App.tsx` - Added route
✅ `frontend/src/components/layout/Layout.tsx` - Added navigation menu item

## Testing Recommendations

1. **Unit Tests**
   - Test `distribute_users_across_accounts()` with various user/account counts
   - Verify remainder handling
   - Test validation (inactive accounts, mismatched IDs)

2. **Integration Tests**
   - Create distribution with 5 accounts
   - Verify 5 jobs created in database
   - Check batch assignments are correct

3. **E2E Tests**
   - Upload 100 user CSV
   - Select 5 accounts
   - Monitor progress on Jobs page
   - Verify all 5 jobs complete

4. **Performance Tests**
   - Time single vs distributed execution
   - Verify speedup is approximately N x faster (where N = number of accounts)

## Future Enhancements

- Support for dynamic account selection based on available capacity
- Adaptive batch sizing based on account performance/trust scores
- Batch rebalancing if an account fails mid-job
- Dashboard showing distribution statistics and speedup metrics
- Ability to pause/resume entire distribution atomically
- Preview of actual user distribution across accounts before submission

## Error Handling

✅ Validates accounts exist and belong to user
✅ Ensures all accounts are active
✅ Requires minimum 2 accounts for distribution
✅ Graceful CSV parsing with error messages
✅ Validates minimum user IDs in CSV
✅ Handles odd distribution evenly with remainder logic
✅ Checks subscription job limits before creation
✅ Proper rollback if batch job creation fails

## Notes

- Feature available to PRO and ENTERPRISE users
- No additional subscription cost
- Works seamlessly with existing mass DM infrastructure
- Batch job type still uses 'mass_dm_account' for execution compatibility
- Parent job type is 'mass_dm_account_distributed' for identification
