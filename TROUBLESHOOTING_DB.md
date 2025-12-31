# Database Connection Troubleshooting

## Issue: "Can't connect to MySQL server (timed out)"

### Possible Causes:

1. **Network/Firewall Issue**: The VPS might not be able to reach the database server
2. **Database Server Not Running**: The MySQL server might be down
3. **Firewall Blocking Port 3306**: The database server's firewall might be blocking connections
4. **Wrong IP Address**: The IP might have changed or be incorrect

### Troubleshooting Steps:

#### 1. Test Network Connectivity

```bash
# Test if you can reach the database server
ping YOUR_DB_HOST

# Test if port 3306 is accessible
telnet YOUR_DB_HOST 3306
# OR
nc -zv YOUR_DB_HOST 3306
```

Replace `YOUR_DB_HOST` with your actual database host from your `.env` file.

#### 2. Check Database Credentials

Verify your `.env` file has the correct credentials:

```bash
cat /var/www/frl-python-api/.env
```

Make sure:
- `DB_HOST` is set to your database host
- `DB_USER` is set to your database username
- `DB_PASSWORD` is correct (with quotes if it contains special characters like `#`)
- `DB_NAME` is set to your database name
- `DB_PORT` is set correctly (usually 3306)

#### 3. Test Database Connection Manually

```bash
# Install MySQL client if not already installed
dnf install mysql -y

# Test connection (replace with your actual credentials)
mysql -h YOUR_DB_HOST -u YOUR_DB_USER -p YOUR_DB_NAME
```

#### 4. Check Firewall Rules

On the database server, make sure:
- MySQL is listening on the correct interface
- Firewall allows connections from your VPS IP
- MySQL user has permission to connect from your VPS IP

#### 5. Check if Database Server is Accessible from PHP App

If the PHP app on the same network can connect, check:
- Is the PHP app on the same server or different server?
- What IP does the PHP app use to connect?

#### 6. Temporary Workaround - Test with Local Connection

If you need to test the app without database access, you can temporarily modify the code to handle connection errors gracefully.

### Updated Code Features:

The updated `database.py` now:
- Uses **lazy connection** (only connects when needed, not at startup)
- Has **retry logic** (3 attempts with 2-second delays)
- Has **connection timeouts** (10 seconds)
- **Auto-reconnects** on connection errors

This means the app should start even if the database is temporarily unavailable, and will connect when you make your first API call.

### Next Steps:

1. **Test network connectivity** first (step 1 above)
2. **Verify credentials** in `.env` file
3. **Check with your network admin** if firewall rules need to be updated
4. **Try starting the app again** - it should start now even if DB is unavailable

