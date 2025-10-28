# 导入必要的库
import streamlit as st  # Streamlit用于创建Web应用界面
import pandas as pd  # Pandas用于数据处理和分析
import plotly.express as px  # Plotly Express用于创建交互式图表
import plotly.graph_objects as go  # Plotly Graph Objects用于更复杂的图表
from datetime import datetime, timedelta  # 用于处理日期和时间
import io  # 用于处理输入输出流

# 设置Streamlit页面配置
st.set_page_config(
    page_title="滞销库存分析仪表板",  # 浏览器标签页标题
    page_icon="📊",  # 浏览器标签页图标
    layout="wide",  # 使用宽屏布局
    initial_sidebar_state="expanded"  # 侧边栏初始状态为展开
)

# 自定义CSS样式，美化界面
# st.markdown("""<style> ... </style>""", unsafe_allow_html=True)
# Streamlit默认会将输入文本视为Markdown，但通过设置unsafe_allow_html=True，它允许在Markdown中直接使用HTML标签，这里使用的是<style>标签

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;   
        color: #1f77b4;  
        text-align: center;  
        margin-bottom: 2rem;  
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
    }
    .positive-change {
        color: #00cc96;
    }
    .negative-change {
        color: #ef553b;
    }
</style>
""", unsafe_allow_html=True)  # unsafe_allow_html=True允许渲染HTML


def detect_encoding(uploaded_file):
    """
    尝试检测文件编码
    参数: uploaded_file - 上传的文件对象
    返回: 检测到的编码字符串
    """
    # 常见的编码列表，按常见程度排序
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin1', 'cp1252', 'iso-8859-1']

    # 保存原始位置，以便后续重置文件指针
    original_position = uploaded_file.tell()

    # 读取文件前10000字节作为样本进行编码检测
    sample = uploaded_file.read(10000)
    uploaded_file.seek(original_position)  # 重置文件指针到原始位置

    # 尝试每种编码
    for encoding in encodings:
        try:
            # 尝试用当前编码解码样本数据
            sample.decode(encoding)
            st.sidebar.info(f"检测到编码: {encoding}")  # 在侧边栏显示检测结果
            return encoding
        except (UnicodeDecodeError, LookupError):
            # 如果解码失败，继续尝试下一种编码
            continue

    # 如果所有编码都失败，使用默认编码并显示警告
    st.sidebar.warning("无法自动检测编码，使用默认编码utf-8")
    return 'utf-8'


def load_data(uploaded_file, manual_encoding=None):
    """
    加载并处理数据，支持多种编码
    参数:
        uploaded_file - 上传的文件对象
        manual_encoding - 手动指定的编码（可选）
    返回: 处理后的DataFrame或None（如果加载失败）
    """
    try:
        # 确定编码：优先使用手动指定的编码，否则自动检测
        if manual_encoding:
            encoding = manual_encoding
        else:
            encoding = detect_encoding(uploaded_file)

        # 尝试使用检测到的编码读取文件
        try:
            df = pd.read_csv(uploaded_file, encoding=encoding)
        except (UnicodeDecodeError, LookupError):
            # 如果检测的编码失败，尝试其他常见编码
            st.sidebar.warning(f"{encoding}编码失败，尝试其他编码...")
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin1', 'cp1252', 'iso-8859-1']
            for enc in encodings:
                try:
                    uploaded_file.seek(0)  # 重置文件指针
                    df = pd.read_csv(uploaded_file, encoding=enc)
                    st.sidebar.success(f"成功使用编码: {enc}")
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                # 所有编码都失败，使用错误处理模式
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='utf-8', errors='replace')
                st.sidebar.warning("使用错误处理模式，部分字符可能显示异常")

        # 定义必要的列名
        required_columns = ['店铺', '品名', '产品类别', 'Msku', '日均', '上月滞销', '本月滞销']

        # 列名映射：支持中英文列名自动匹配
        column_mapping = {
            '店铺': ['店铺', 'store', 'Shop', '门店'],
            '品名': ['品名', '产品名称', 'product', 'Product', '商品名称'],
            '产品类别': ['产品类别', 'category', 'Category', '品类'],
            'Msku': ['Msku', 'MSKU', 'sku', 'SKU'],
            '日均': ['日均', '日均销量', 'daily', 'Daily', '平均销量'],
            '上月滞销': ['上月滞销', '上月滞销数量', 'last_month', 'LastMonth', '上月库存'],
            '本月滞销': ['本月滞销', '本月滞销数量', 'this_month', 'ThisMonth', '本月库存']
        }

        # 自动匹配列名：查找实际文件中的列名与标准列名的对应关系
        actual_columns = {}
        for standard_col, possible_names in column_mapping.items():
            for possible_name in possible_names:
                if possible_name in df.columns:
                    actual_columns[standard_col] = possible_name
                    break  # 找到第一个匹配就停止，避免重复 break僅僅針對第二個循環，找到就停止

        # actual_columns 的结构：
        # {
        #     '标准列名1': '实际列名1',
        #     '标准列名2': '实际列名2',
        #     # ...
        # }

        # 检查是否找到了所有必要列
        missing_columns = [col for col in required_columns if col not in actual_columns]
        if missing_columns:
            st.error(f"缺少必要列: {missing_columns}")
            st.info(f"当前文件包含的列: {list(df.columns)}")
            return None

        # 重命名列为标准名称，便于后续处理
        df = df.rename(columns=actual_columns)

        # 转换数值列：将文本格式的数字转换为数值类型
        numeric_columns = ['日均', '上月滞销', '本月滞销']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')  # coerce参数将无法转换的值设为NaN

        # 填充空值：将NaN值替换为0
        df = df.fillna(0)

        # 计算滞销数量变化：本月滞销 - 上月滞销
        df['滞销数量变化'] = df['本月滞销'] - df['上月滞销']
        # 计算变化百分比，避免除零错误
        df['变化百分比'] = (df['滞销数量变化'] / df['上月滞销'].replace(0, 1)) * 100

        # 显示数据基本信息
        st.sidebar.info(f"数据行数: {len(df)}")

        return df  # 返回处理后的数据

    except Exception as e:
        # 捕获并显示任何异常
        st.error(f"数据加载失败: {str(e)}")
        return None


def create_summary_metrics(df):
    """
    创建汇总指标卡片
    参数: df - 处理后的数据DataFrame
    """
    # 创建4列布局用于显示指标
    col1, col2, col3, col4 = st.columns(4)

    # 计算关键指标
    total_current = df['本月滞销'].sum()  # 本月总滞销数量
    total_previous = df['上月滞销'].sum()  # 上月总滞销数量
    total_change = total_current - total_previous  # 总变化量
    change_percentage = (total_change / total_previous * 100) if total_previous > 0 else 0  # 变化百分比

    # 在第一列显示本月总滞销数量
    with col1:
        st.metric(
            label="本月总滞销数量",
            value=f"{total_current:,.0f}",  # 格式化数字，添加千位分隔符
            delta=f"{total_change:+,.0f} ({change_percentage:+.1f}%)"  # 显示变化量和百分比
        )

    # 在第二列显示平均日均销量
    with col2:
        avg_daily = df['日均'].mean()
        st.metric(
            label="平均日均销量",
            value=f"{avg_daily:.1f}"  # 保留一位小数
        )

    # 在第三列显示滞销产品数量
    with col3:
        products_count = df['品名'].nunique()  # 计算唯一产品数量
        st.metric(
            label="滞销产品数量",
            value=f"{products_count:,}"  # 格式化数字，添加千位分隔符
        )

    # 在第四列显示涉及店铺数量
    with col4:
        stores_count = df['店铺'].nunique()  # 计算唯一店铺数量
        st.metric(
            label="涉及店铺数量",
            value=f"{stores_count:,}"  # 格式化数字，添加千位分隔符
        )


def create_trend_chart(df, group_by='产品类别'):
    """
    创建滞销趋势图表
    参数:
        df - 处理后的数据DataFrame
        group_by - 分组维度
    返回: Plotly图表对象
    """
    if group_by == '日期':
        # 如果有日期数据，按日期分组
        trend_data = df.groupby('日期').agg({
            '上月滞销': 'sum',
            '本月滞销': 'sum'
        }).reset_index()

        # 创建折线图
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend_data['日期'], y=trend_data['上月滞销'],
                                 name='上月滞销', line=dict(dash='dot')))  # 虚线表示上月
        fig.add_trace(go.Scatter(x=trend_data['日期'], y=trend_data['本月滞销'],
                                 name='本月滞销', line=dict(color='red')))  # 红色实线表示本月

    else:
        # 按其他维度分组（产品类别或店铺）
        trend_data = df.groupby(group_by).agg({
            '上月滞销': 'sum',
            '本月滞销': 'sum'
        }).reset_index()

        # 创建分组柱状图
        fig = go.Figure(data=[
            go.Bar(name='上月滞销', x=trend_data[group_by], y=trend_data['上月滞销']),
            go.Bar(name='本月滞销', x=trend_data[group_by], y=trend_data['本月滞销'])
        ])

    # 更新图表布局
    fig.update_layout(
        title=f'按{group_by}分组的滞销趋势对比',
        xaxis_title=group_by,
        yaxis_title='滞销数量',
        barmode='group',  # 分组柱状图模式
        height=400  # 设置图表高度
    )

    return fig


def create_comparison_chart(df):
    """
    创建对比分析图表
    参数: df - 处理后的数据DataFrame
    返回: 两个Plotly图表对象
    """
    # 创建滞销变化分布直方图
    fig1 = px.histogram(df, x='滞销数量变化',
                        title='滞销数量变化分布',
                        labels={'滞销数量变化': '滞销数量变化量'})
    fig1.update_layout(height=300)

    # 创建店铺滞销排名柱状图
    store_data = df.groupby('店铺').agg({
        '本月滞销': 'sum',
        '滞销数量变化': 'sum'
    }).reset_index().sort_values('本月滞销', ascending=False).head(10)  # 取前10名

    fig2 = px.bar(store_data, x='店铺', y='本月滞销',
                  title='店铺滞销数量TOP10',
                  color='滞销数量变化',  # 用颜色表示变化量
                  color_continuous_scale='RdYlGn_r')  # 红-黄-绿色标，反向
    fig2.update_layout(height=300)

    return fig1, fig2


def show_instructions():
    """显示使用说明和数据格式要求"""
    st.info("👈 请在侧边栏上传CSV文件开始分析")

    # 显示示例数据结构
    st.header("📝 数据格式要求")

    # 创建两列布局
    col1, col2 = st.columns(2)

    # 在左列显示中文列名示例
    with col1:
        st.subheader("中文列名示例")
        example_data_cn = pd.DataFrame({
            '店铺': ['店铺A', '店铺A', '店铺B'],
            '品名': ['产品A', '产品B', '产品C'],
            '产品类别': ['类别1', '类别2', '类别1'],
            'Msku': ['MSKU001', 'MSKU002', 'MSKU003'],
            '日均': [10, 5, 8],
            '上月滞销': [100, 50, 80],
            '本月滞销': [120, 40, 90]
        })
        st.dataframe(example_data_cn, use_container_width=True)

    # 在右列显示英文列名示例
    with col2:
        st.subheader("英文列名示例")
        example_data_en = pd.DataFrame({
            'store': ['StoreA', 'StoreA', 'StoreB'],
            'product': ['ProductA', 'ProductB', 'ProductC'],
            'category': ['Category1', 'Category2', 'Category1'],
            'Msku': ['MSKU001', 'MSKU002', 'MSKU003'],
            'daily': [10, 5, 8],
            'last_month': [100, 50, 80],
            'this_month': [120, 40, 90]
        })
        st.dataframe(example_data_en, use_container_width=True)

    # 显示解决编码问题的步骤
    st.markdown("""
    ### 解决编码问题的步骤:

    1. **在Excel中另存为UTF-8格式**:
       - 文件 → 另存为
       - 选择"CSV UTF-8"格式
       - 保存后重新上传

    2. **检查列名一致性**:
       - 确保包含所有必要列
       - 列名可以是中文或英文

    3. **检查数据内容**:
       - 数值列不要包含文本字符
       - 确保没有特殊字符影响解析
    """)


def main():
    """主函数，组织整个应用的逻辑"""
    # 显示主标题
    st.markdown('<div class="main-header">📊 滞销库存统计及对比分析仪表板</div>',
                unsafe_allow_html=True)

    # 侧边栏文件上传部分
    st.sidebar.header("数据上传")

    # 文件上传器
    uploaded_file = st.sidebar.file_uploader(
        "上传CSV文件",
        type=['csv'],
        help="支持UTF-8、GBK、GB2312等编码格式"
    )

    # 手动编码选择下拉框
    encoding_option = st.sidebar.selectbox(
        "选择编码（如自动检测失败）",
        ["自动检测", "utf-8", "gbk", "gb2312", "latin1", "cp1252"]
    )

    # 检查是否有文件上传
    if uploaded_file is not None:
        # 显示文件基本信息
        file_details = {
            "文件名": uploaded_file.name,
            "文件大小": f"{uploaded_file.size / 1024:.1f} KB"  # 转换为KB并保留一位小数
        }
        st.sidebar.write("文件信息:")
        for key, value in file_details.items():
            st.sidebar.write(f"- {key}: {value}")

        # 加载数据
        if encoding_option == "自动检测":
            df = load_data(uploaded_file)
        else:
            df = load_data(uploaded_file, manual_encoding=encoding_option)

        # 如果自动检测失败，提供手动选择
        if df is None and encoding_option == "自动检测":
            st.warning("自动编码检测失败，请手动选择编码格式")
            manual_encoding = st.selectbox(
                "手动选择编码",
                ["utf-8", "gbk", "gb2312", "latin1", "cp1252"],
                key="manual_encoding"  # 唯一的key，避免Streamlit组件冲突
            )
            if st.button("重新加载文件"):
                df = load_data(uploaded_file, manual_encoding=manual_encoding)

        # 如果数据加载成功
        if df is not None:
            # 显示成功消息
            st.sidebar.success("数据加载成功!")

            # 侧边栏数据筛选部分
            st.sidebar.header("数据筛选")

            # 店铺筛选下拉框
            stores = ['全部'] + sorted(df['店铺'].unique().tolist())  # 添加"全部"选项
            selected_store = st.sidebar.selectbox('选择店铺', stores)

            # 产品类别筛选下拉框
            categories = ['全部'] + sorted(df['产品类别'].unique().tolist())  # 添加"全部"选项
            selected_category = st.sidebar.selectbox('选择产品类别', categories)

            # 应用筛选条件
            filtered_df = df.copy()  # 创建数据副本，避免修改原始数据
            if selected_store != '全部':
                filtered_df = filtered_df[filtered_df['店铺'] == selected_store]
            if selected_category != '全部':
                filtered_df = filtered_df[filtered_df['产品类别'] == selected_category]

            # 显示数据概览部分
            st.header("📈 数据概览")
            create_summary_metrics(filtered_df)  # 创建并显示汇总指标

            # 滞销趋势分析部分
            st.header("📊 滞销趋势分析")

            # 创建两列布局
            col1, col2 = st.columns(2)

            # 左列：滞销趋势图表
            with col1:
                group_by_option = st.selectbox(
                    "选择分组维度",
                    ['产品类别', '店铺']  # 可选的分类维度
                )
                trend_fig = create_trend_chart(filtered_df, group_by_option)
                st.plotly_chart(trend_fig, use_container_width=True)  # 使用容器宽度

            # 右列：滞销产品TOP10
            with col2:
                # 获取滞销最严重的10个产品
                top_products = filtered_df.nlargest(10, '本月滞销')[['品名', '本月滞销', '滞销数量变化']]
                fig_top = px.bar(top_products, x='品名', y='本月滞销',
                                 title='滞销产品TOP10',
                                 color='滞销数量变化',  # 用颜色表示变化量
                                 color_continuous_scale='RdYlGn_r')  # 红-黄-绿色标，反向
                fig_top.update_layout(height=400, xaxis_tickangle=-45)  # 设置高度和x轴标签角度
                st.plotly_chart(fig_top, use_container_width=True)

            # 对比分析部分
            st.header("🔍 对比分析")
            fig1, fig2 = create_comparison_chart(filtered_df)  # 创建两个对比图表

            # 创建两列布局显示对比图表
            col3, col4 = st.columns(2)
            with col3:
                st.plotly_chart(fig1, use_container_width=True)  # 滞销变化分布
            with col4:
                st.plotly_chart(fig2, use_container_width=True)  # 店铺滞销排名

            # 详细数据表格部分
            st.header("📋 详细数据")

            # 数据筛选选项
            col5, col6 = st.columns(2)
            with col5:
                # 多选框选择要显示的列
                show_columns = st.multiselect(
                    "选择显示列",
                    options=filtered_df.columns.tolist(),
                    default=['店铺', '品名', '产品类别', '本月滞销', '滞销数量变化', '变化百分比']
                )

            with col6:
                # 选择排序方式和顺序
                sort_by = st.selectbox("排序方式", options=filtered_df.columns.tolist())
                sort_order = st.radio("排序顺序", ["降序", "升序"], horizontal=True)  # 水平排列的单选按钮

            # 应用排序
            display_df = filtered_df[show_columns] if show_columns else filtered_df
            display_df = display_df.sort_values(
                sort_by,
                ascending=(sort_order == "升序")  # 根据选择设置升序或降序
            )

            # 显示数据表格
            st.dataframe(display_df, use_container_width=True)

            # 数据导出部分
            st.header("📤 数据导出")

            # 创建两列布局
            col7, col8 = st.columns(2)

            # 左列：导出CSV文件
            with col7:
                # 将数据转换为CSV格式
                csv = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="导出筛选数据为CSV",
                    data=csv,
                    file_name=f"滞销分析数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

            # 右列：生成分析报告
            with col8:
                if st.button("生成分析报告"):
                    # 创建分析报告文本
                    report_text = f"""
滞销库存分析报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

总体情况:
- 本月总滞销数量: {filtered_df['本月滞销'].sum():,.0f}
- 上月总滞销数量: {filtered_df['上月滞销'].sum():,.0f}
- 滞销变化: {filtered_df['滞销数量变化'].sum():+,.0f}
- 平均日均销量: {filtered_df['日均'].mean():.1f}

涉及范围:
- 产品数量: {filtered_df['品名'].nunique():,}
- 店铺数量: {filtered_df['店铺'].nunique():,}
- 产品类别: {filtered_df['产品类别'].nunique():,}

滞销最严重的产品:
{filtered_df.nlargest(5, '本月滞销')[['品名', '本月滞销']].to_string(index=False)}
"""
                    # 显示分析报告文本框
                    st.text_area("分析报告", report_text, height=300)

        else:
            # 数据加载失败时的错误提示
            st.error("""
            **数据加载失败，请尝试以下解决方案:**

            1. **检查文件编码**: 在Excel中另存为时选择"CSV UTF-8"格式
            2. **检查列名**: 确保包含必要的列名
            3. **检查数据格式**: 确保数值列没有文本字符
            """)

    else:
        # 没有上传文件时显示使用说明
        show_instructions()


# Python标准的主程序入口
if __name__ == "__main__":
    main()  # 调用主函数启动应用