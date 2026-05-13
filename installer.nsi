; NSIS Installer Script -- 资质代办全网推广助手
; 用法: makensis installer.nsi   (需先执行 build.bat)

!include "MUI2.nsh"
!include "FileFunc.nsh"

; ------ 基本信息 ------
!define PRODUCT_NAME "资质代办全网推广助手"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "QualificationBot"
!define PRODUCT_WEB_SITE "https://www.example.com"

Name "${PRODUCT_NAME}"
OutFile "dist\${PRODUCT_NAME}_v${PRODUCT_VERSION}_Setup.exe"
InstallDir "$PROGRAMFILES\${PRODUCT_NAME}"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
BrandingText "${PRODUCT_NAME} v${PRODUCT_VERSION}"

; ------ 界面 ------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "assets\license.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

; ------ 安装 ------
Section "Install"
    SetOutPath "$INSTDIR"

    ; 主程序
    File /r "dist\QualificationPromoteBot\*"

    ; 创建数据目录
    CreateDirectory "$INSTDIR\data"
    CreateDirectory "$INSTDIR\data\logs"
    CreateDirectory "$INSTDIR\data\profiles"
    CreateDirectory "$INSTDIR\data\screenshots"
    CreateDirectory "$INSTDIR\data\exports"

    ; 快捷方式
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\资质代办推广助手.lnk" "$INSTDIR\QualificationPromoteBot.exe"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\卸载.lnk" "$INSTDIR\uninst.exe"
    CreateShortCut "$DESKTOP\资质代办推广助手.lnk" "$INSTDIR\QualificationPromoteBot.exe"

    ; 卸载程序
    WriteUninstaller "$INSTDIR\uninst.exe"

    ; 注册表 (添加/删除程序)
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "UninstallString" "$INSTDIR\uninst.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "NoRepair" 1

    ; 估算安装大小
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
        "EstimatedSize" "$0"
SectionEnd

; ------ 卸载 ------
Section "Uninstall"
    RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"
    Delete "$DESKTOP\资质代办推广助手.lnk"
    RMDir /r "$INSTDIR"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
SectionEnd
