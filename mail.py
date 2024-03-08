import smtplib
from email.mime.text import MIMEText
from email.header import Header

def send_email(sender_email, smtp_password, receiver_email, subject, body):
    # 设置SMTP服务器和端口号
    smtp_server = 'smtp.qq.com'
    smtp_port = 465
    
    # 创建一个MIMEText对象，定义邮件正文和字符编码
    message = MIMEText(body, 'plain', 'utf-8')
    
    # 设置邮件的头部信息
    message['From'] = Header(sender_email)
    message['To'] = Header(receiver_email)
    message['Subject'] = Header(subject, 'utf-8')
    
    try:
        # 连接到SMTP服务器
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        
        # 登录SMTP服务器
        server.login(sender_email, smtp_password)
        
        # 发送邮件
        server.sendmail(sender_email, [receiver_email], message.as_string())
        
        # 关闭连接
        server.quit()
        
        print("邮件发送成功")
    except smtplib.SMTPException as e:
        print("邮件发送失败", e)