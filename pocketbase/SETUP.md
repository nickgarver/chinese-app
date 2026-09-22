# PocketBase setup

The app works with no server at all — progress falls back to localStorage. You
only need PocketBase if you want IDs that carry progress between devices.

## 1. Run it

Download the binary for your platform from pocketbase.io/docs, then:

```bash
./pocketbase serve --http 0.0.0.0:8090
```

Open http://127.0.0.1:8090/_/ and create the admin account.

Point the app at it with a `.env` file in the project root:

```
VITE_PB_URL=http://127.0.0.1:8090
```

## 2. Collections

### `users` (auth collection — already exists by default)

In **Options**, enable **username/password** authentication and turn off the
email requirement. The app never asks for an email address.

The client generates a single ID like `jade-tiger-x7k2m9q4wp3n` and derives the
PocketBase password from it with SHA-256, so the ID alone signs in on any
device. The password is not a second secret — **the ID is the whole
credential**, which is why it carries about 62 bits of randomness.

If your PocketBase version requires an email field, set it optional. Do not
enable "Forgot password" — there is no address to send it to, and a lost ID
cannot be recovered.

### `progress` (base collection)

| Field        | Type     | Options                          |
| ------------ | -------- | -------------------------------- |
| `user`       | Relation | → users, single, cascade delete, **required** |
| `cards`      | JSON     | max size 2 MB                    |
| `updated_at` | Text     |                                  |

Add a **unique index** on `user` so a user can't end up with two rows:

```sql
CREATE UNIQUE INDEX idx_progress_user ON progress (user);
```

### API rules on `progress`

Set all five rules to the same expression. This is the part that actually stops
one person reading another's data, so don't leave any of them empty:

```
@request.auth.id != "" && user = @request.auth.id
```

For **Create**, use:

```
@request.auth.id != "" && @request.body.user = @request.auth.id
```

### API rules on `users`

- List/Search: leave **locked** (admin only). Otherwise anyone can enumerate IDs.
- View: `id = @request.auth.id`
- Create: leave open so the app can generate accounts.
- Update/Delete: `id = @request.auth.id`

## 3. Backups

SQLite lives in `pb_data/`. Copy it while the server is stopped, or run
[Litestream](https://litestream.io) to replicate continuously:

```yaml
# litestream.yml
dbs:
  - path: /opt/pocketbase/pb_data/data.db
    replicas:
      - type: s3
        bucket: your-bucket
        path: hsk-pb
```

If you're running on a Raspberry Pi, put `pb_data` on a USB SSD rather than the
SD card. SD cards have poor random-write endurance and a database workload is
the fastest way to kill one.

## Note on the security model

The ID is a bearer credential. Anyone who has it has full access to that
progress, and there is no recovery if it's lost. That is the trade for having no
signup. Three things follow:

- **Keep the random tail long.** It is the only thing standing between a
  stranger and someone's account. Shortening it to look nicer would be a real
  downgrade — at 12 base36 characters, guessing is infeasible; at 4, it isn't.
- Keep the `users` list rule locked so IDs can't be enumerated.
- Consider PocketBase's built-in rate limiting, since the ID is guessable in
  principle even if not in practice.

If you later want real recovery, the smallest change is to let users optionally
attach an email to an existing account.
