#!/bin/bash
set -e

# Run database migrations
alembic upgrade head

# Execute the command passed to the script
exec "$@"
```

After this, I will construct the message to the user.
