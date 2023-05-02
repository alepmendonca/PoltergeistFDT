# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
exec('import datetime') or \
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=(0, 0, 0, 0),
    prodvers=(0, 0, 0, 0),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x4,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '000004b0',
        [StringStruct('CompanyName', 'Receita Estadual de Sao Paulo'),
        StringStruct('FileDescription', 'PoltergeistFDT para SRE-SP'),
        StringStruct('InternalName', 'PoltergeistFDT.exe'),
        StringStruct('LegalCopyright', f'Copyleft © {datetime.date.today().year}'),
        StringStruct('OriginalFilename', 'PoltergeistFDT.exe'),
        StringStruct('ProductName', 'PoltergeistFDT'),
        StringStruct('ProductVersion', f'0.5.1-{datetime.datetime.now().strftime("%Y%m%d%H")}')])
      ]), 
    VarFileInfo([VarStruct('Translation', [0, 1200])])
  ]
)