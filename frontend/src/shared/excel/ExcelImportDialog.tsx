import type { UploadFile, UploadProps } from "antd"
import { Alert, App, Button, Modal, Table, Upload } from "antd"
import type { ColumnsType } from "antd/es/table"
import { Download, Upload as UploadIcon } from "lucide-react"
import { useState } from "react"
import {
  type ExcelIssue,
  getExcelValidationFailure,
  validateXlsxFile,
} from "@/shared/excel/excel"

type ExcelImportDialogProps = {
  onClose: () => void
  onDownloadTemplate: () => Promise<unknown>
  onImport: (file: File) => Promise<unknown>
  open: boolean
  title: string
}

const issueColumns: ColumnsType<ExcelIssue> = [
  { dataIndex: "worksheet", render: (value) => value ?? "-", title: "工作表" },
  { dataIndex: "row", render: (value) => value ?? "-", title: "行", width: 72 },
  { dataIndex: "column", render: (value) => value ?? "-", title: "列" },
  { dataIndex: "field", render: (value) => value ?? "-", title: "字段" },
  { dataIndex: "message", title: "问题" },
]

export function ExcelImportDialog({
  onClose,
  onDownloadTemplate,
  onImport,
  open,
  title,
}: ExcelImportDialogProps) {
  const { message } = App.useApp()
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [issues, setIssues] = useState<ExcelIssue[]>([])
  const [issueMessage, setIssueMessage] = useState<string>()
  const [isDownloading, setDownloading] = useState(false)
  const [isSubmitting, setSubmitting] = useState(false)

  const reset = () => {
    setFileList([])
    setIssues([])
    setIssueMessage(undefined)
  }
  const close = () => {
    if (isSubmitting) return
    reset()
    onClose()
  }
  const beforeUpload: UploadProps["beforeUpload"] = (file) => {
    const validationError = validateXlsxFile(file)
    if (validationError) {
      message.error(validationError)
      return Upload.LIST_IGNORE
    }
    setFileList([file])
    setIssues([])
    setIssueMessage(undefined)
    return false
  }
  const downloadTemplate = async () => {
    setDownloading(true)
    try {
      await onDownloadTemplate()
    } catch {
      message.error("模板下载失败，请稍后重试。")
    } finally {
      setDownloading(false)
    }
  }
  const submit = async () => {
    const file = fileList[0]?.originFileObj
    if (!file) {
      message.error("请选择要导入的工作簿。")
      return
    }
    setSubmitting(true)
    setIssues([])
    setIssueMessage(undefined)
    try {
      await onImport(file)
      reset()
      onClose()
    } catch (error) {
      const failure = getExcelValidationFailure(error)
      if (failure) {
        setIssueMessage(failure.message)
        setIssues(failure.issues)
      } else {
        message.error("导入失败，请稍后重试。")
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      destroyOnHidden
      footer={[
        <Button key="cancel" onClick={close}>
          取消
        </Button>,
        <Button
          key="submit"
          loading={isSubmitting}
          onClick={() => void submit()}
          type="primary"
        >
          导入
        </Button>,
      ]}
      onCancel={close}
      open={open}
      title={title}
      width={issues.length > 0 ? 960 : 520}
    >
      <div className="flex flex-col gap-4">
        <Button
          icon={<Download size={16} />}
          loading={isDownloading}
          onClick={() => void downloadTemplate()}
        >
          下载模板
        </Button>
        <Upload
          accept=".xlsx"
          beforeUpload={beforeUpload}
          fileList={fileList}
          maxCount={1}
          onRemove={() => {
            setFileList([])
          }}
        >
          <Button icon={<UploadIcon size={16} />}>选择工作簿</Button>
        </Upload>
        {issueMessage ? <Alert message={issueMessage} type="error" /> : null}
        {issues.length > 0 ? (
          <Table
            columns={issueColumns}
            dataSource={issues}
            pagination={false}
            rowKey={(issue, index) =>
              [
                issue.worksheet,
                issue.row,
                issue.column,
                issue.field,
                index,
              ].join("-")
            }
            scroll={{ x: 800, y: 320 }}
            size="small"
          />
        ) : null}
      </div>
    </Modal>
  )
}
