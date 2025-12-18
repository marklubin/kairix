#!/bin/bash
set -e

DEVICE_ID="00008120-001C79E11A400032"
DEVICE_NAME="mark's iPhone"
SCHEME="iosApp"
PROJECT="iosApp/iosApp.xcodeproj"
CONFIG="${1:-Debug}"
BUILD_DIR="build/ios"

echo "==> Building KMP framework for iOS arm64..."
./gradlew linkDebugFrameworkIosArm64

echo "==> Building iOS app ($CONFIG)..."
xcodebuild \
    -project "$PROJECT" \
    -scheme "$SCHEME" \
    -configuration "$CONFIG" \
    -sdk iphoneos \
    -derivedDataPath "$BUILD_DIR" \
    -destination "id=$DEVICE_ID" \
    build \
    2>&1 | grep -E "(error:|warning:|BUILD|Compiling|Linking|\*\*)" || true

APP_PATH="$BUILD_DIR/Build/Products/$CONFIG-iphoneos/iosApp.app"

if [ ! -d "$APP_PATH" ]; then
    echo "Error: App not found at $APP_PATH"
    exit 1
fi

echo "==> Deploying to $DEVICE_NAME..."
ios-deploy --id "$DEVICE_ID" --bundle "$APP_PATH" --justlaunch

echo "==> Done! App launched on $DEVICE_NAME"
