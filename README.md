# Phone Emulator Manager

[![Buy Me A Coffee](https://img.shields.io/badge/Buy_Me_A_Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/coreyess)

Video: https://www.youtube.com/watch?v=y2c7Ue-es3U

A sleek, free, and open-source graphical user interface (GUI) for managing and launching mobile emulators across platforms without ever touching the command line.

## 🚀 The Problem

If you're a developer, QA tester, or OSINT investigator, you know the pain of spinning up an emulator. The traditional workflow requires opening up a terminal, trying to remember exactly what you named your virtual device, remembering the exact flags for memory limits or core usage, and typing out long commands like:
`emulator -avd Pixel_8_API_35 -memory 6144 -cores 4`

If you forget the exact name of the device, you have to run `emulator -list-avds` just to figure it out, interrupting your workflow. If you're switching between Android, iOS, HarmonyOS, and Amazon Fire OS, the terminal gymnastics only get worse as each SDK has its own rules.

## ✨ The Solution

**Phone Emulator Manager** replaces all of that CLI friction with a beautiful, high-contrast, midnight-blue GUI that sits quietly in your Windows system tray. 

* **One-Click Launch:** See all your installed emulators at a glance and start them with a single click. 
* **Universal Support:** Seamlessly create and manage virtual devices across Android, Apple iOS, Huawei HarmonyOS, and Amazon Fire OS.
* **Auto-Categorized Library:** The app automatically categorizes Google SDK outputs, sorting them cleanly into their proper Makes and Models (including Generic sizes, Desktop, TV, Automotive, and Wearables).
* **Massive Device Library:** Out-of-the-box support for hundreds of the newest physical devices up to 2026, including the latest foldables and tablets.
* **No More Terminal:** Create new AVDs, delete old ones, and launch them with robust hardware flags—all through a polished interface instead of a command prompt.

## 🛠️ Prerequisites

To run emulators, you must have the underlying SDK installed for the respective platform:
* **Android & Amazon Fire OS:** Requires [Android Studio](https://developer.android.com/studio).
* **Huawei HarmonyOS:** Requires [DevEco Studio](https://developer.huawei.com/consumer/en/deveco-studio/).
* **Apple iOS:** Requires [Xcode](https://apps.apple.com/us/app/xcode/id497799835) (Mac only).

## 📥 Installation

1. Download the standalone installer.
2. Run `PhoneEmulatorManager_Setup.exe`.
3. The app will quietly run in your system tray, accessible whenever you need to spin up a virtual phone!
