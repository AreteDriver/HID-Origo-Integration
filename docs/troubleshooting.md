# Part 3: Troubleshooting Scenarios

## Question 1: Wallet Provisioning Failure

### Error: `OrigoKeysErrorCodeSecureElementNotAvailable`

**What does this error indicate?**

This error means the HID Mobile Access SDK cannot access the device's Secure Element (SE), which is required for storing mobile credentials securely. The Secure Element is a tamper-resistant hardware component that stores cryptographic keys and credentials.

---

### Three Possible Causes

#### 1. Device Compatibility Issue
- **Description**: The device doesn't have a supported Secure Element
- **Common scenarios**:
  - Older iPhone models (pre-iPhone 6)
  - Android devices without NFC or embedded SE
  - Android devices where SE access is restricted by manufacturer
  - Virtual machines or emulators (no physical SE)

#### 2. Apple Wallet / Google Wallet Configuration
- **Description**: The wallet platform isn't properly configured
- **Common scenarios**:
  - Apple Wallet: No cards added (SE not initialized)
  - Apple Wallet: Apple Pay not set up in region
  - Google Wallet: Google Pay disabled
  - Google Wallet: NFC disabled in device settings
  - Enterprise MDM policies blocking wallet access

#### 3. App Entitlements / Permissions Missing
- **Description**: The app lacks required entitlements to access SE
- **Common scenarios**:
  - iOS: Missing NFC entitlement in app capabilities
  - iOS: Missing `com.apple.developer.payment-pass-provisioning` entitlement
  - Android: Missing `NFC` permission in AndroidManifest.xml
  - Android: Missing HID Origo SDK initialization
  - App not properly signed with correct provisioning profile

---

### Troubleshooting Steps

```
STEP 1: Verify Device Compatibility
───────────────────────────────────
□ Check device model against HID Origo compatibility list
□ Verify device has NFC capability
□ Confirm device OS version meets minimum requirements
  - iOS: 13.0+
  - Android: 8.0+ (API 26)
□ Test on physical device (not emulator/simulator)

STEP 2: Check Wallet Configuration
──────────────────────────────────
iOS:
□ Open Wallet app
□ Verify at least one card is added (initializes SE)
□ Check Settings > Wallet & Apple Pay
□ Ensure region supports Apple Pay

Android:
□ Open Google Wallet app
□ Verify Google Pay is set up
□ Check Settings > Connected devices > NFC (enabled)
□ Verify HCE (Host Card Emulation) is supported

STEP 3: Verify App Configuration
────────────────────────────────
iOS:
□ Check Xcode project capabilities:
  - Near Field Communication Tag Reading
  - Access Wifi Information (sometimes required)
□ Verify Info.plist contains NFCReaderUsageDescription
□ Confirm provisioning profile includes NFC entitlements
□ Check that app is signed with correct certificate

Android:
□ Verify AndroidManifest.xml permissions:
  <uses-permission android:name="android.permission.NFC" />
  <uses-feature android:name="android.hardware.nfc" android:required="true" />
□ Check that HID Origo SDK is properly initialized
□ Verify minSdkVersion >= 26

STEP 4: SDK Initialization Check
────────────────────────────────
□ Verify SDK version matches platform requirements
□ Check SDK initialization occurs before provisioning call
□ Review SDK logs for additional error details
□ Confirm issuance token is valid and not expired

STEP 5: Environment Verification
────────────────────────────────
□ Confirm correct Origo environment (sandbox vs production)
□ Verify pass template is configured for correct platform
□ Check organization settings in Origo portal
□ Test with a known-working device first

STEP 6: Escalation Path
───────────────────────
If above steps don't resolve:
□ Collect SDK logs (enable verbose logging)
□ Note device model, OS version, app version
□ Document exact error message and stack trace
□ Contact HID support with collected information
```

---

## Question 2: App Crashes After SDK Upgrade

### Scenario: App crashes when initializing `OrigoKeysManager` after upgrading SDK

---

### Possible Migration Issues

#### 1. Swift Version Mismatch (iOS)
```
Error: Module compiled with Swift X.Y cannot be imported by Swift X.Z
```
- SDK compiled with different Swift version than your project
- ABI compatibility issues between Swift versions
- **Solution**: Match Xcode/Swift version to SDK requirements

#### 2. Framework Encryption / Bitcode Issues (iOS)
```
Error: Bitcode bundle could not be generated
```
- SDK may not support Bitcode
- Framework encryption settings mismatch
- **Solution**: Disable Bitcode if SDK doesn't support it:
  ```
  Build Settings > Enable Bitcode = NO
  ```

#### 3. Missing CocoaPods Updates (iOS)
```
Error: Unable to find specification for 'OrigoKeys'
```
- Pod cache contains outdated version
- Podspec path changed in new version
- Local pod cache corrupted
- **Solution**: Clean install (see procedure below)

#### 4. Minimum Deployment Target Changed
- New SDK may require higher iOS/Android version
- **Solution**: Update deployment target in project settings

#### 5. API Breaking Changes
- Method signatures changed
- Deprecated APIs removed
- New required initialization parameters
- **Solution**: Review SDK changelog and migration guide

#### 6. ProGuard / R8 Rules (Android)
```
Error: ClassNotFoundException: OrigoKeysManager
```
- Obfuscation rules stripping SDK classes
- **Solution**: Add ProGuard rules from SDK documentation

---

### Clean Upgrade Procedure

#### iOS (CocoaPods)

```bash
# Step 1: Close Xcode completely
# (Important: Xcode locks files)

# Step 2: Remove existing pods and cache
rm -rf Pods/
rm -rf ~/Library/Caches/CocoaPods/
rm Podfile.lock

# Step 3: Clear derived data
rm -rf ~/Library/Developer/Xcode/DerivedData/

# Step 4: Update CocoaPods repo
pod repo update

# Step 5: Update Podfile with new SDK version
# Edit Podfile:
#   pod 'HIDOrigoSDK', '~> X.Y.Z'

# Step 6: Fresh install
pod install --repo-update

# Step 7: Open workspace (NOT .xcodeproj)
open YourApp.xcworkspace

# Step 8: Clean build
# In Xcode: Product > Clean Build Folder (Cmd+Shift+K)

# Step 9: Build and run
```

#### iOS (Swift Package Manager)

```bash
# Step 1: Close Xcode

# Step 2: Remove package cache
rm -rf ~/Library/Caches/org.swift.swiftpm/
rm -rf .build/

# Step 3: Reset package resolution
# In Xcode: File > Packages > Reset Package Caches

# Step 4: Update package version in Package.swift or Xcode

# Step 5: Resolve packages
# File > Packages > Resolve Package Versions

# Step 6: Clean and rebuild
```

#### Android (Gradle)

```bash
# Step 1: Close Android Studio

# Step 2: Clean Gradle caches
./gradlew clean
rm -rf ~/.gradle/caches/

# Step 3: Update SDK version in build.gradle
# dependencies {
#     implementation 'com.hidglobal.origo:sdk:X.Y.Z'
# }

# Step 4: Sync project
./gradlew --refresh-dependencies

# Step 5: Rebuild
./gradlew assembleDebug
```

---

### Xcode Version Compatibility Check

```bash
# Check current Xcode version
xcodebuild -version

# Check Swift version
swift --version

# Verify against SDK requirements:
# HID Origo SDK typically requires:
# - Xcode 14.0+ for iOS 16 features
# - Xcode 15.0+ for iOS 17 features
# - Swift 5.7+ for modern concurrency
```

---

### Post-Upgrade Verification Checklist

```
□ App builds without errors
□ App launches without crashes
□ OrigoKeysManager initializes successfully
□ Can authenticate and get token
□ Can enumerate existing credentials
□ New provisioning works correctly
□ Existing credentials still function
□ NFC/BLE access works
□ No new deprecation warnings (or acknowledged)
□ All unit tests pass
□ Integration tests pass
```

---

## Common Error Codes Reference

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| `SecureElementNotAvailable` | No SE access | Check device compatibility, wallet setup |
| `InvalidIssuanceToken` | Token expired/used | Generate new token |
| `NetworkError` | Connection failed | Check internet, retry |
| `AuthenticationFailed` | Bad credentials | Verify client_id/secret |
| `PassTemplateNotFound` | Invalid template ID | Verify template exists in org |
| `UserNotFound` | Invalid user ID | Create user first |
| `PassAlreadyProvisioned` | Duplicate provision | Check pass status |
| `DeviceNotSupported` | Incompatible device | Use supported device |
| `RegionNotSupported` | Geographic restriction | Check region settings |
