import time
import sys
import webbrowser
import requests

DEVICE_CODE_URL = "https://api.simkl.com/oauth2/device"
TOKEN_URL = "https://api.simkl.com/oauth2/token"

def main():
    print("==================================================")
    print("        Simkl AUTH V2 Device Token Helper        ")
    print("==================================================")
    print("This tool uses Simkl's modern AUTH V2 (RFC 8628).")
    print("No client secret or redirect URL required!\n")

    client_id = input("Enter your Simkl Client ID: ").strip()
    if not client_id:
        print("Error: Client ID cannot be empty.")
        return

    # Request device code
    payload = {
        "client_id": client_id,
        "scope": "media:read media:write"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "DoubanToSimklSync/2.0"
    }

    print("\n[1/3] Requesting device code from Simkl...")
    try:
        resp = requests.post(DEVICE_CODE_URL, data=payload, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"Error: Failed to request device code (Status {resp.status_code}): {resp.text}")
            return
        data = resp.json()
    except Exception as e:
        print(f"Network error requesting device code: {e}")
        return

    device_code = data.get("device_code")
    user_code = data.get("user_code")
    verification_uri_complete = data.get("verification_uri_complete")
    verification_uri = data.get("verification_uri", "https://simkl.com/pin")
    interval = data.get("interval", 5)
    expires_in = data.get("expires_in", 900)

    print("\n[2/3] Authorization Required:")
    print(f"  * Your User PIN Code : {user_code}")
    print(f"  * Direct Approval URL: {verification_uri_complete}")
    print(f"  * Fallback URL       : {verification_uri} (enter {user_code})")

    # Try opening the browser automatically
    try:
        print("\nOpening your default browser for authorization...")
        webbrowser.open(verification_uri_complete)
    except Exception:
        print("Could not open browser automatically. Please click or open the link manually.")

    print("\n[3/3] Polling for approval (press Ctrl+C to cancel)...")
    start_time = time.time()
    
    poll_payload = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": client_id,
        "device_code": device_code
    }

    while True:
        if time.time() - start_time > expires_in:
            print("\nError: Device authorization code expired. Please run the script again.")
            break

        time.sleep(interval)

        try:
            poll_resp = requests.post(TOKEN_URL, data=poll_payload, headers=headers, timeout=15)
            
            if poll_resp.status_code == 200:
                token_data = poll_resp.json()
                access_token = token_data.get("access_token")
                refresh_token = token_data.get("refresh_token")
                
                print("\n================== SUCCESS ==================")
                print("Successfully obtained Simkl AUTH V2 tokens!")
                print("=============================================")
                print(f"\n1. SIMKL_CLIENT_ID:\n{client_id}")
                print(f"\n2. SIMKL_ACCESS_TOKEN:\n{access_token}")
                print(f"\n3. SIMKL_REFRESH_TOKEN:\n{refresh_token}")
                print("\n=============================================")
                print("Next Steps:")
                print("1. Go to your GitHub repository -> Settings > Secrets and variables > Actions.")
                print("2. Add or update:")
                print("   - SIMKL_CLIENT_ID")
                print("   - SIMKL_ACCESS_TOKEN")
                print("   - SIMKL_REFRESH_TOKEN")
                print("\nNote: Because the Refresh Token is non-rotating, your GitHub Action")
                print("will perpetually renew access tokens automatically without manual intervention!")
                break
                
            error_data = poll_resp.json() if poll_resp.text else {}
            error_code = error_data.get("error")

            if error_code == "authorization_pending":
                # Still waiting for user approval
                sys.stdout.write(".")
                sys.stdout.flush()
                continue
            elif error_code == "slow_down":
                interval += 5
                print(f"\nRate limit warning: increasing polling interval to {interval}s...")
                continue
            elif error_code == "expired_token":
                print("\nError: The device code has expired. Please restart the script.")
                break
            elif error_code == "invalid_client":
                print(f"\nError: Invalid Client ID ({client_id}). Ensure it was registered as a V2 App.")
                break
            else:
                print(f"\nUnexpected response ({poll_resp.status_code}): {poll_resp.text}")
                break

        except KeyboardInterrupt:
            print("\nPolling cancelled by user.")
            break
        except Exception as e:
            print(f"\nPolling error: {e}")
            time.sleep(interval)

if __name__ == "__main__":
    main()
