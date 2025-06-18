import React, { useState } from 'react';
import { Upload, Button, message, Spin, Card, Modal, Input, Tag, Statistic, Collapse, Empty, Select } from 'antd';
import { UploadOutlined, DownloadOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons';
import axios from 'axios';
import { io } from 'socket.io-client';
import './App.css';

const { Panel } = Collapse;
const { Option } = Select;

const classifyMethods = [
  { value: 'keyword', label: '一般关键词分类' },
  { value: 'smart_keyword', label: '智能关键词分类（实时抓取网页标题）' },
  { value: 'tfidf', label: 'TF-IDF 语义聚类' },
  { value: 'folder', label: '原始文件夹结构分类' },
  { value: 'domain', label: '按域名分类' },
];

function App() {
  const [uploading, setUploading] = useState(false);
  const [fileName, setFileName] = useState('');
  const [bookmarks, setBookmarks] = useState([]);
  const [classified, setClassified] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [showClassified, setShowClassified] = useState(false);
  const [classifyMethod, setClassifyMethod] = useState('keyword');
  const [logRecords, setLogRecords] = useState([]);

  // 上传书签文件
  const handleUpload = ({ file }) => {
    setUploading(true);
    setShowClassified(false);
    setClassified([]);
    const formData = new FormData();
    formData.append('file', file);
    axios.post('/api/upload', formData).then(res => {
      setFileName(res.data.filename);
      message.success('上传成功，正在解析...');
      axios.post('/api/parse', { filename: res.data.filename }).then(res2 => {
        setBookmarks(res2.data.bookmarks);
        setUploading(false);
        message.success('解析完成，可进行分类');
      });
    }).catch(() => {
      setUploading(false);
      message.error('上传失败');
    });
  };

  // 智能分类（WebSocket实时日志）
  const handleClassify = () => {
    setLoading(true);
    setLogRecords([]);
    if (classifyMethod === 'smart_keyword') {
      const socket = io('http://localhost:5000');
      socket.emit('smart_keyword_classify', { bookmarks });
      socket.on('smart_keyword_log', (data) => {
        setLogRecords(prev => [...prev, data.log]);
      });
      socket.on('smart_keyword_result', (data) => {
        setClassified(data.result);
        setShowClassified(true);
        setLoading(false);
        socket.disconnect();
        message.success('分类完成');
      });
      socket.on('connect_error', () => {
        setLoading(false);
        message.error('WebSocket连接失败');
        socket.disconnect();
      });
    } else {
      axios.post('/api/classify', { bookmarks, method: classifyMethod }).then(res => {
        setClassified(res.data.classified);
        setShowClassified(true);
        setLoading(false);
        if (res.data.logs) setLogRecords(res.data.logs);
        message.success('分类完成');
      });
    }
  };

  // 导出书签
  const handleExport = () => {
    axios.post('/api/export', { bookmarks: classified }, { responseType: 'blob' }).then(res => {
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', '分类书签.html');
      document.body.appendChild(link);
      link.click();
      link.remove();
      message.success('导出成功');
    });
  };

  // 搜索功能
  const filtered = search ? classified.filter(b => b.title.includes(search) || b.url.includes(search)) : classified;

  return (
    <div style={{ padding: 24 }}>
      <h1>书签智能分类与管理</h1>
      <Upload customRequest={handleUpload} showUploadList={false} accept=".html">
        <Button icon={<UploadOutlined />} loading={uploading}>上传书签文件</Button>
      </Upload>
      <Select
        value={classifyMethod}
        onChange={setClassifyMethod}
        style={{ width: 240, margin: '0 8px' }}
        options={classifyMethods}
      />
      <Button onClick={handleClassify} disabled={!bookmarks.length} style={{ margin: 8 }}>智能分类</Button>
      <Button onClick={handleExport} disabled={!classified.length} icon={<DownloadOutlined />}>导出书签</Button>
      <Input prefix={<SearchOutlined />} placeholder="搜索书签" value={search} onChange={e => setSearch(e.target.value)} style={{ width: 300, margin: 8 }} />
      {/* 原始书签展示，可折叠 */}
      <Collapse style={{ margin: '16px 0' }} defaultActiveKey={['1']}>
        <Panel header={`原始书签（共${bookmarks.length}条）`} key="1">
          {bookmarks.length === 0 ? <Empty description="请先上传书签文件" /> : (
            <div className="cards-container">
              {bookmarks.map((b, i) => (
                <Card key={i} title={<span className="title-text" title={b.title}>{b.title}</span>} extra={<a href={b.url} target="_blank" rel="noopener noreferrer">访问</a>} style={{ width: 300 }}>
                  <div className="url-text" title={b.url}>URL: {b.url}</div>
                  <div>文件夹: <Tag>{b.folder}</Tag></div>
                  <div>添加时间: {b.add_date}</div>
                </Card>
              ))}
            </div>
          )}
        </Panel>
      </Collapse>
      {/* 分类结果展示，仅分类后显示 */}
      {showClassified && (
        <Spin spinning={loading} tip="处理中...">
          <div style={{ margin: '16px 0' }}>
            <Statistic title="书签总数" value={classified.length} />
          </div>
          <div className="cards-container">
            {filtered.map((b, i) => (
              <Card key={i} title={<span className="title-text" title={b.title}>{b.title}</span>} extra={<a href={b.url} target="_blank" rel="noopener noreferrer">访问</a>} style={{ width: 300 }}>
                <div className="url-text" title={b.url}>URL: {b.url}</div>
                <div>分类: <Tag color="blue">{b.category || '未分类'}</Tag></div>
                <div>标签: {b.tags && b.tags.map(t => <Tag key={t}>{t}</Tag>)}</div>
                <Button icon={<EditOutlined />} size="small" style={{ marginRight: 8 }}>编辑</Button>
                <Button icon={<DeleteOutlined />} size="small" danger>删除</Button>
              </Card>
            ))}
          </div>
        </Spin>
      )}
      {classifyMethod === 'smart_keyword' && (
        <div style={{
          background: '#222', color: '#fff', fontFamily: 'monospace', fontSize: 13,
          height: 180, overflowY: 'auto', margin: '12px 0', borderRadius: 6, padding: 8
        }}>
          <div>智能抓取日志：</div>
          <div style={{ whiteSpace: 'pre-line' }}>
            {logRecords.length === 0 ? '正在抓取网页标题...' : logRecords.map((line, i) => <div key={i}>{line}</div>)}
          </div>
        </div>
      )}
    </div>
  );
}

export default App; 