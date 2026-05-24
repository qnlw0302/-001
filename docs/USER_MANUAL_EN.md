# Inventory Management User Manual

This is a desktop app for tracking your own product inventory on your computer.
All data lives on your machine — nothing is uploaded to the internet.

## 1. Install and Launch the App

**macOS**

1. Locate `InventoryManagement.app` (in the `build/desktop/` folder of the
   download, or wherever your administrator placed it).
2. Drag it into your **Applications** folder (optional but recommended).
3. The first time you open it, macOS shows a security warning because the
   app is not signed. **Right-click → Open**, then click **Open** in the
   confirmation dialog. After the first launch, double-click works normally.

**Windows**

1. Locate `InventoryManagement.exe` inside the `InventoryManagement` folder.
2. Double-click to launch.
3. The first time you open it, Windows SmartScreen may show "Windows
   protected your PC." Click **More info → Run anyway**.
4. On Windows 10, if the window fails to appear and no error shows, install
   the free Microsoft Edge **WebView2 Runtime** from Microsoft's website,
   then re-launch. (Windows 11 has it pre-installed.)

A window opens. You do not need to start any other program — the app is
fully self-contained.

## 2. Choose a Language

A **Language** selector appears at the top of the login, registration, and
inventory screens.

- Choose **English** for English.
- Choose **中文** for Chinese.
- Your choice is remembered on this computer.

## 3. Create an Account

The very first time you launch the app, the **Welcome** registration screen
opens automatically (there are no users yet).

1. Enter a username.
2. Enter a password with at least 6 characters.
3. Re-enter the password to confirm.
4. Check **Remember me** if you want to stay signed in across restarts.
5. Click **Create Account**.

After at least one account exists, the app shows the login screen on launch.
You can still register additional accounts from there by clicking
**Create one**.

## 4. Log In and Log Out

To log in:

1. Enter your username.
2. Enter your password.
3. Check **Remember me** if you want to.
4. Click **Log In**.

To leave the app, click **Log Out** at the top of the inventory screen, or
just close the window.

## 5. Read the Dashboard

The top of the inventory screen shows:

- **Total Products**: how many products you have.
- **Low Stock**: products whose stock has dropped below their alert threshold.
- **Out of Stock**: products with a stock quantity of zero.
- **Default restock alert**: the threshold used for any product without a
  custom one.

Each user account only sees its own inventory.

## 6. Add a Product

Use the **Insert Product** form on the left.

1. Enter a unique **SKU**.
2. Enter the **Product Name**.
3. Enter the initial **Stock Quantity**.
4. Optionally set a **Low Stock Alert** threshold.
5. Optionally add **Custom Fields** (category, supplier, color, shelf,
   cost, etc.).
6. Click **Insert Product**.

The initial stock you enter is automatically recorded as the first entry in
the product's stock history.

## 7. Find and View Products

Use the search box to filter by SKU or product name.

- Click **Search** to apply, **Reset** to clear.
- Use **Previous** and **Next** to page through long lists.
- Click **Get** in a product row to load its details on the right.
- Or enter a product ID under **Get Product** and click **Get Product**.

## 8. Update or Delete a Product

To update product details:

1. Load a product with **Get** or **Get Product**.
2. Edit SKU, name, low-stock threshold, or custom fields.
3. Click **Save Changes**.

The **Stock Quantity** field is intentionally locked while editing — see
section 9 for how to change stock.

To delete a product:

1. Click **Delete** in the product row, or **Delete Product** after loading
   one.
2. Re-enter your password to confirm.
3. Click **Delete**.

## 9. Manage Stock

Stock is changed only through these row buttons, never by editing the
product directly. Every action is recorded in history with a timestamp,
quantity change, and optional note.

- **Receive**: add stock (arrivals or returns). The modal lets you pick
  the reason — *Stock arrival* or *Customer return*.
- **Remove**: subtract stock (sales, usage, damage, loss). The modal lets
  you pick the reason — *Sold or used* or *Damaged or lost*.
- **Adjust**: set the absolute stock level after a recount or correction.
  You can adjust down to zero.
- **History**: open a list of recent stock changes for that product.

Add a note when it helps — supplier name, sale reference, recount details,
damage cause.

If you try to remove more units than are in stock, the app rejects the
change and tells you how many are actually left.

## 10. Export Products

Click **Export** in the top bar to download your inventory as
`products.csv`. The file goes to your computer's normal downloads location.

## 11. Manage Your Account

- **Edit Profile**: change your username. You must confirm with your
  current password.
- **Change Password**: enter your current password and pick a new one
  (minimum 6 characters; common passwords like `123456` are rejected).

## 12. Backup and Reset

The app keeps everything in your computer's standard application-data folder.
Copy this folder to back up; delete it to start over.

| OS      | Folder                                                                |
|---------|-----------------------------------------------------------------------|
| macOS   | `~/Library/Application Support/InventoryManagement/`                  |
| Windows | `%LOCALAPPDATA%\InventoryManagement\InventoryManagement\`             |

Inside that folder:

- `inventory.db` — all your products, users, and stock history.
- `secret_key` — used to sign your login session; do not share.
- `logs/` — application logs (useful when reporting a problem).

**To back up**: copy the whole folder somewhere safe.

**To restore**: replace the folder with your backup (while the app is closed).

**To start over**: close the app and delete the folder. The next launch
creates a fresh database and prompts you to register again.

## 13. Common Problems

- **Window doesn't open on Windows**: install the Microsoft Edge WebView2
  Runtime (free from Microsoft's website), then re-launch.
- **"Windows protected your PC"**: click **More info → Run anyway**. This
  appears because the build is not code-signed yet.
- **macOS "cannot be opened because the developer cannot be verified"**:
  right-click the app → **Open** → **Open** in the dialog.
- **Invalid username or password**: check your credentials and try again.
  After 5 failed attempts the account is temporarily locked for 15 minutes.
- **SKU already exists**: each SKU must be unique within your account.
- **Cannot remove N units: only M in stock**: the requested removal would
  drive stock negative. Either receive more first or remove less.
- **Session expired**: log in again.
- **I forgot my password**: there is no password reset — close the app,
  delete `inventory.db` from the folder in section 12, then relaunch and
  register again. (Your products will be lost; back up first if needed.)
