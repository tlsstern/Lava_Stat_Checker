# Migration Guide - Separate player_names Table

This guide helps you migrate from using the shared `players` table to a dedicated `player_names` table for the Lava Stat Checker.

## Why This Change?

The `players` table is used by another project, so we're creating a separate `player_names` table specifically for Lava Stat Checker to avoid conflicts.

## Migration Steps

### 1. Run the Migration SQL

Run the contents of `create_player_names_table.sql` in your Supabase SQL editor. This will:

1. Create a new `player_names` table
2. Drop and recreate the `stats` table to reference `player_names` instead of `players`
3. Recreate all necessary functions and policies

```sql
-- The script will:
-- 1. Create player_names table
-- 2. Recreate stats table with proper foreign key
-- 3. Set up all RLS policies
-- 4. Recreate helper functions
```

### 2. What Changes

#### Before:
- Stats referenced `players` table (shared with other project)
- `players` table had additional columns like `category`

#### After:
- Stats reference new `player_names` table (dedicated to this project)
- `player_names` table only has: `uuid`, `player_name`, `updated_at`
- No interference with your other project

### 3. Data Structure

The new `player_names` table:
```sql
CREATE TABLE player_names (
    uuid TEXT PRIMARY KEY,
    player_name TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4. No Code Changes Needed

The Supabase handler has been updated to use `player_names` automatically. Your app will work seamlessly after running the migration SQL.

### 5. Verify Migration

After running the SQL, verify:
1. `player_names` table exists
2. `stats` table references `player_names` (not `players`)
3. Test by searching for a player - it should cache correctly

## Rollback (If Needed)

If you need to rollback:
```sql
DROP TABLE IF EXISTS stats CASCADE;
DROP TABLE IF EXISTS player_names CASCADE;
-- Then recreate your original structure
```

## Benefits

- **Isolation**: Your Lava Stat Checker data is completely separate
- **No Conflicts**: Won't interfere with your other project using `players` table
- **Cleaner Schema**: Only stores what's needed for Bedwars stats