// XSIZETools_CppHelpers
// C++ Helpers to speed up .msh exporting.

#include <xsi_application.h>
#include <xsi_context.h>
#include <xsi_pluginregistrar.h>
#include <xsi_status.h>

#include <xsi_string.h>
#include <xsi_argument.h>
#include <xsi_command.h>
#include <xsi_x3dobject.h>
#include <xsi_primitive.h>
#include <xsi_polygonmesh.h>
#include <xsi_geometryaccessor.h>
#include <xsi_longarray.h>
#include <xsi_floatarray.h>
#include <xsi_doublearray.h>
#include <xsi_clusterproperty.h>
#include <xsi_envelopeweight.h>

#include <xsi_material.h>
#include <xsi_point.h>

#include <xsi_utils.h>

#include <vector>


// Change callback for different SDK versions (x86 version needs to support older versions of XSI and only newer versions have x64 support).
#ifdef _WIN64
#define CALLBACK SICALLBACK
#else
#define CALLBACK XSIPLUGINCALLBACK CStatus
#endif

using namespace XSI; 
using namespace MATH;

class VertexData {
public:
	int index = 0;
	int nodeIndex = 0;
	float x, y, z = 0.f;
	float nx, ny, nz = 0.f;
	float u, v = 0.f;
	float weights[4] = { 0.f, 0.f, 0.f, 0.f };
	int deformers[4] = { 0, 0, 0, 0 };
};

CALLBACK XSILoadPlugin( PluginRegistrar& in_reg )
{
	in_reg.PutAuthor(L"Benedikt 'Schlechtwetterfront' Schatz");
	in_reg.PutName(L"CGeoAccessorWrappers");
	in_reg.PutVersion(0,8);
	
	in_reg.RegisterCommand(L"CGA_GetVertexIndices",L"CGA_GetVertexIndices");
	in_reg.RegisterCommand(L"CGA_GetNodeIndices",L"CGA_GetNodeIndices");
	in_reg.RegisterCommand(L"CGA_GetVertexPositions",L"CGA_GetVertexPositions");
	in_reg.RegisterCommand(L"CGA_GetPolygonVerticesCount",L"CGA_GetPolygonVerticesCount");
	in_reg.RegisterCommand(L"CGA_GetNodeNormals",L"CGA_GetNodeNormals");
	in_reg.RegisterCommand(L"CGA_GetUV0",L"CGA_GetUV0");
	in_reg.RegisterCommand(L"CGA_GetVertexColors0",L"CGA_GetVertexColors0");
	in_reg.RegisterCommand(L"CGA_GetNodeVertexPositions",L"CGA_GetNodeVertexPositions");
	in_reg.RegisterCommand(L"CGA_GetWeights0",L"CGA_GetWeights0");
	in_reg.RegisterCommand(L"CGA_GetWeightsZE",L"CGA_GetWeightsZE");
	in_reg.RegisterCommand(L"CGA_GetDeformers0",L"CGA_GetDeformers0");
	in_reg.RegisterCommand(L"CGA_GetNodesPerPoint",L"CGA_GetNodesPerPoint");

	in_reg.RegisterCommand(L"ZET_GetVertexPositionsWithNormals", L"ZET_GetVertexPositionsWithNormals");
	in_reg.RegisterCommand(L"ZET_GetUVs", L"ZET_GetUVs");
	in_reg.RegisterCommand(L"ZET_GetWeights", L"ZET_GetWeights");
	in_reg.RegisterCommand(L"ZET_GetPolyVertexIndicesAndCounts", L"ZET_GetPolyVertexIndicesAndCounts");
	in_reg.RegisterCommand(L"ZET_GetPolyMaterialIndices", L"ZET_GetPolyMaterialIndices");
	in_reg.RegisterCommand(L"ZET_GetMaterialNames", L"ZET_GetMaterialNames");
	in_reg.RegisterCommand(L"ZET_GetGeometry", L"ZET_GetGeometry");

	return CStatus::OK;
}

CALLBACK XSIUnloadPlugin( const PluginRegistrar& in_reg )
{
	CString strPluginName;
	strPluginName = in_reg.GetName();
	Application().LogMessage(strPluginName + L" has been unloaded.",siVerboseMsg);
	return CStatus::OK;
}


CALLBACK ZET_GetGeometry_Init(CRef& in_ctxt)
{
	Context context(in_ctxt);

	Command command;
	command = context.GetSource();

	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	arguments.Add(L"calculateWorldCoordinates", true);
	command.PutDescription(L"Returns an array containing vertex positions plus their normals in a flat array. If calculateWorldCoordinates is true, multiply the vertex positions with the object's scale.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK ZET_GetGeometry_Execute(CRef& in_ctxt)
{
	Context ctxt(in_ctxt);
	Application xsi;

	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh polyMesh = args[0];
	bool calculateWorldCoordinates = args[1];

	CLongArray nodeIndices;
	ga.GetNodeIndices(nodeIndices);

	CFloatArray nodeNormals;
	ga.GetNodeNormals(nodeNormals);

	CLongArray vertexIndices;
	ga.GetVertexIndices(vertexIndices);

	CDoubleArray vertexPositions;
	ga.GetVertexPositions(vertexPositions);

	CLongArray nodeToVertex(nodeIndices.GetCount());

	std::vector<VertexData> vertices;

	for (long j = 0; j < nodeIndices.GetCount(); j++) {
		long vertexIndex = vertexIndices[j];
		long nodeIndex = nodeIndices[j];
		nodeToVertex[nodeIndex] = vertexIndex;
	}

	// Double the length so we can put the normals in the same array.
	CFloatArray result;
	result.Resize(vertexPositions.GetCount() * 2);

	// Get the scale of the object this geometry belongs to so we can calculate world coordinates.
	MATH::CTransformation transform = ga.GetTransform();
	double scaleX = transform.GetSclX(), scaleY = transform.GetSclY(), scaleZ = transform.GetSclZ();

	for (long i = 0; i < vertexIndices.GetCount(); i++) {
		long nodeIndex = nodeIndices[i];
		long vertexIndex = vertexIndices[i];

		VertexData* v = new VertexData();
		v->index = vertexIndex;
		v->nodeIndex = nodeIndex;

		v->x = vertexPositions[vertexIndex * 3] * scaleX;
		v->y = vertexPositions[vertexIndex * 3 + 1] * scaleY;
		v->z = vertexPositions[vertexIndex * 3 + 2] * scaleZ;

		v->nx = nodeNormals[nodeIndex * 3];
		v->ny = nodeNormals[nodeIndex * 3 + 1];
		v->nz = nodeNormals[nodeIndex * 3 + 2];
	}

	/*CPointRefArray points = polyMesh.GetPoints();
	
	for (long i = 0; i < points.GetCount(); i++) {
		Point point = points[i];
		CVector3 position = point.GetPosition();
		bool isNormalValid = true;
		CVector3 normal = point.GetNormal(isNormalValid);
		point.get
	}*/

	ctxt.PutAttribute(L"ReturnValue", result);
	return CStatus::OK;
}


CALLBACK ZET_GetVertexPositionsWithNormals_Init(CRef& in_ctxt)
{
	Context context(in_ctxt);

	Command command;
	command = context.GetSource();

	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	arguments.Add(L"calculateWorldCoordinates", true);
	command.PutDescription(L"Returns an array containing vertex positions plus their normals in a flat array. If calculateWorldCoordinates is true, multiply the vertex positions with the object's scale.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK ZET_GetVertexPositionsWithNormals_Execute(CRef& in_ctxt)
{
	Context ctxt(in_ctxt);
	Application xsi;

	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh polyMesh = args[0];
	bool calculateWorldCoordinates = args[1];

	CGeometryAccessor ga = polyMesh.GetGeometryAccessor();

	CLongArray nodeIndices;
	ga.GetNodeIndices(nodeIndices);

	CFloatArray nodeNormals;
	ga.GetNodeNormals(nodeNormals);

	CLongArray vertexIndices;
	ga.GetVertexIndices(vertexIndices);

	CDoubleArray vertexPositions;
	ga.GetVertexPositions(vertexPositions);

	// Double the length so we can put the normals in the same array.
	CFloatArray result;
	result.Resize(vertexPositions.GetCount() * 2);

	// Get the scale of the object this geometry belongs to so we can calculate world coordinates.
	MATH::CTransformation transform = ga.GetTransform();
	double scaleX = transform.GetSclX(), scaleY = transform.GetSclY(), scaleZ = transform.GetSclZ();

	for (long i = 0; i < vertexIndices.GetCount(); i++) {
		long nodeIndex = nodeIndices[i];
		long vertexIndex = vertexIndices[i];
		if (calculateWorldCoordinates) {
			result[vertexIndex * 6] = vertexPositions[vertexIndex * 3] * scaleX;
			result[vertexIndex * 6 + 1] = vertexPositions[vertexIndex * 3 + 1] * scaleY;
			result[vertexIndex * 6 + 2] = vertexPositions[vertexIndex * 3 + 2] * scaleZ;
		}
		else {
			result[vertexIndex * 6] = vertexPositions[vertexIndex * 3];
			result[vertexIndex * 6 + 1] = vertexPositions[vertexIndex * 3 + 1];
			result[vertexIndex * 6 + 2] = vertexPositions[vertexIndex * 3 + 2];
		}
		result[vertexIndex * 6 + 3] = nodeNormals[nodeIndex * 3];
		result[vertexIndex * 6 + 3 + 1] = nodeNormals[nodeIndex * 3 + 1];
		result[vertexIndex * 6 + 3 + 2] = nodeNormals[nodeIndex * 3 + 2];
	}

	ctxt.PutAttribute(L"ReturnValue", result);
	return CStatus::OK;
}


CALLBACK ZET_GetUVs_Init(CRef& in_ctxt)
{
	Context ctxt(in_ctxt);
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	arguments.Add(L"uvSetIndex", 0);
	command.PutDescription(L"Returns UV values of the UV cluster wiht index uvSetIndex.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK ZET_GetUVs_Execute(CRef& in_ctxt)
{
	Context ctxt(in_ctxt);
	Application xsi;

	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh polyMesh = args[0];
	long uvSetIndex = args[1];

	CGeometryAccessor ga = polyMesh.GetGeometryAccessor();

	CRefArray uvs = ga.GetUVs();

	ClusterProperty uv = uvs[uvSetIndex];

	CFloatArray uvCoordinates;
	uv.GetValues(uvCoordinates);

	ctxt.PutAttribute(L"ReturnValue", uvCoordinates);
	return CStatus::OK;
}


CALLBACK ZET_GetPolyMaterialIndices_Init(CRef& in_ctxt)
{
	Context ctxt(in_ctxt);
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	command.PutDescription(L"Returns a flat list of indices where the index represents the index of the polygon and the stored value the index of the material.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK ZET_GetPolyMaterialIndices_Execute(CRef& in_ctxt)
{
	Context ctxt(in_ctxt);
	Application xsi;

	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh polyMesh = args[0];

	CGeometryAccessor ga = polyMesh.GetGeometryAccessor();

	CLongArray polyMaterialIndices;
	ga.GetPolygonMaterialIndices(polyMaterialIndices);

	ctxt.PutAttribute(L"ReturnValue", polyMaterialIndices);
	return CStatus::OK;
}


CALLBACK ZET_GetMaterialNames_Init(CRef& in_ctxt)
{
	Context ctxt(in_ctxt);
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	command.PutDescription(L"Returns a list of all materials used by this object.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK ZET_GetMaterialNames_Execute(CRef& in_ctxt)
{
	Context ctxt(in_ctxt);
	Application xsi;

	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh polyMesh = args[0];

	CGeometryAccessor ga = polyMesh.GetGeometryAccessor();

	CRefArray materials = ga.GetMaterials();

	CValueArray materialNames(materials.GetCount());

	for (int i = 0; i < materials.GetCount(); i++) {
		Material material(materials[i]);
		materialNames[i] = material.GetName();
	}

	ctxt.PutAttribute(L"ReturnValue", materialNames);
	return CStatus::OK;
}


CALLBACK ZET_GetWeights_Init(CRef& in_ctxt)
{
	Context ctxt(in_ctxt);
	Command command;
	command = ctxt.GetSource();

	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	arguments.Add(L"envelopePropertyIndex", 0);
	command.PutDescription(L"Returns ( [weights], [deformernames] ). A PolygonMesh needs to be passed as argument.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK ZET_GetWeights_Execute(CRef& in_ctxt)
{
	Context ctxt(in_ctxt);
	Application xsi;
	
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh polyMesh = args[0];
	long envelopePropertyIndex = args[1];

	CGeometryAccessor ga = polyMesh.GetGeometryAccessor();

	CRefArray envWeights = ga.GetEnvelopeWeights();

	EnvelopeWeight envWeight = envWeights[envelopePropertyIndex];

	CFloatArray weights;
	envWeight.GetValues(weights);

	long valueSize = envWeight.GetValueSize();

	// Declare arrays.
	CValueArray deformerNames(valueSize);

	CRefArray deformers = envWeight.GetDeformers();
	deformerNames.Resize(deformers.GetCount());

	for (long j = 0; j<deformers.GetCount(); j++) {
		SIObject siobj(deformers[j]);
		deformerNames[j] = siobj.GetName();
	}
	CValueArray resultArray(2);

	resultArray[0] = weights;
	resultArray[1] = deformerNames;
	ctxt.PutAttribute(L"ReturnValue", resultArray);
	return CStatus::OK;
}


CALLBACK ZET_GetPolyVertexIndicesAndCounts_Init(CRef& in_ctxt)
{
	Context ctxt(in_ctxt);
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	command.PutDescription(L"Wrapper for CGeometryAccessor method GetVertexIndices. Returns a flat array of vertex indices for every polygon (1,2,44,5 , 3,4,5; for two polygons with 4 and 3 sides) and a flat array of per-poly vertex counts.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK ZET_GetPolyVertexIndicesAndCounts_Execute(CRef& in_ctxt)
{
	Context ctxt(in_ctxt);
	Application xsi;

	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh polyMesh = args[0];

	CGeometryAccessor ga = polyMesh.GetGeometryAccessor();

	CLongArray vertexIndices;
	ga.GetVertexIndices(vertexIndices);

	CLongArray polyVertexCounts;
	ga.GetPolygonVerticesCount(polyVertexCounts);

	CValueArray returnArray(2);
	returnArray[0] = vertexIndices;
	returnArray[1] = polyVertexCounts;

	ctxt.PutAttribute(L"ReturnValue", returnArray);
	return CStatus::OK;
}


CALLBACK CGA_GetNodeVertexPositions_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	arguments.Add(L"worldCoords");
	command.PutDescription(L"Returns the corresponding vertex position for every node in an array. If worldCoords is True, multiply with scale.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetNodeVertexPositions_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh obj = args[0];
	bool worldCoords = args[1];
	CGeometryAccessor ga = obj.GetGeometryAccessor();
	// get poly node indices
	CLongArray nodeindices;
	ga.GetNodeIndices(nodeindices);
	// get poly vert indices
	CLongArray vertindices;
	ga.GetVertexIndices(vertindices);
	// get vert positions
	CDoubleArray vertpos;
	ga.GetVertexPositions(vertpos);
	//
	CFloatArray positions;
	positions.Resize(nodeindices.GetCount()*3);
	// format
	if(worldCoords == true) {
		MATH::CTransformation transform = ga.GetTransform();
		double sX = transform.GetSclX();
		double sY = transform.GetSclY();
		double sZ = transform.GetSclZ();
		for(long i=0; i<vertindices.GetCount(); i++) {
			// Order Vertices after Nodes.
			long nodeindex = nodeindices[i];
			long vertindex = vertindices[i];
			positions[nodeindex*3] = vertpos[vertindex*3]*sX;
			positions[nodeindex*3+1] = vertpos[vertindex*3+1]*sY;
			positions[nodeindex*3+2] = vertpos[vertindex*3+2]*sZ;
		}
	}
	else {
		for(long i=0; i<vertindices.GetCount(); i++) {
			long nodeindex = nodeindices[i];
			long vertindex = vertindices[i];
			positions[nodeindex*3] = vertpos[vertindex*3];
			positions[nodeindex*3+1] = vertpos[vertindex*3+1];
			positions[nodeindex*3+2] = vertpos[vertindex*3+2];
		}
	}
	ctxt.PutAttribute( L"ReturnValue", positions);
	return CStatus::OK;
}

CALLBACK CGA_GetVertexIndices_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	command.PutDescription(L"\"Wrapper\" for CGeometryAccessor method GetVertexIndices. A PolygonMesh needs to be passed as argument.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetVertexIndices_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh obj = args[0];
	CGeometryAccessor ga = obj.GetGeometryAccessor();
	CLongArray vertindices;
	ga.GetVertexIndices(vertindices);
	ctxt.PutAttribute( L"ReturnValue", vertindices);
	// Return CStatus::Fail if you want to raise a script error
	return CStatus::OK;
}

CALLBACK CGA_GetNodeIndices_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	command.PutDescription(L"\"Wrapper\" for CGeometryAccessor method GetNodeIndices. A PolygonMesh needs to be passed as argument.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetNodeIndices_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh obj = args[0];
	CGeometryAccessor ga = obj.GetGeometryAccessor();
	CLongArray nodeindices;
	ga.GetNodeIndices(nodeindices);
	ctxt.PutAttribute( L"ReturnValue", nodeindices);
	// Return CStatus::Fail if you want to raise a script error
	return CStatus::OK;
}

CALLBACK CGA_GetVertexPositions_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	command.PutDescription(L"\"Wrapper\" for CGeometryAccessor method GetVertexPositions. A PolygonMesh needs to be passed as argument.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetVertexPositions_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh obj = args[0];
	CGeometryAccessor ga = obj.GetGeometryAccessor();
	CDoubleArray vertpositions;
	ga.GetVertexPositions(vertpositions);
	long doublecount = vertpositions.GetCount();
	CFloatArray vertpos;
	vertpos.Resize(doublecount);
	for(long i=0; i<doublecount; i++) {
		vertpos[i] = vertpositions[i];
	}
	ctxt.PutAttribute( L"ReturnValue", vertpos);
	// Return CStatus::Fail if you want to raise a script error
	return CStatus::OK;
}

CALLBACK CGA_GetPolygonVerticesCount_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	command.PutDescription(L"\"Wrapper\" for CGeometryAccessor method GetVerticesCount. A PolygonMesh needs to be passed as argument.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetPolygonVerticesCount_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh obj = args[0];
	CGeometryAccessor ga = obj.GetGeometryAccessor();
	CLongArray polyvertcnt;
	ga.GetPolygonVerticesCount(polyvertcnt);
	ctxt.PutAttribute( L"ReturnValue", polyvertcnt);
	// Return CStatus::Fail if you want to raise a script error
	return CStatus::OK;
}

CALLBACK CGA_GetNodeNormals_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	command.PutDescription(L"\"Wrapper\" for CGeometryAccessor method GetNodeNormals. A PolygonMesh needs to be passed as argument.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetNodeNormals_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh obj = args[0];
	CGeometryAccessor ga = obj.GetGeometryAccessor();
	CFloatArray normals;
	ga.GetNodeNormals(normals);
	ctxt.PutAttribute( L"ReturnValue", normals);
	// Return CStatus::Fail if you want to raise a script error
	return CStatus::OK;
}

CALLBACK CGA_GetUV0_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	command.PutDescription(L"Returns UV values as CFloatArray of the first UV cluster. A PolygonMesh needs to be passed as argument.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetUV0_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh geo = args[0];
	CGeometryAccessor ga = geo.GetGeometryAccessor();
	CRefArray uvs = ga.GetUVs();
	ClusterProperty uv = uvs[0];
	CFloatArray uvvalues;
	uv.GetValues(uvvalues);
	ctxt.PutAttribute( L"ReturnValue", uvvalues );
	return CStatus::OK;
}

CALLBACK CGA_GetVertexColors0_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	command.PutDescription(L"Returns vertex color values of the first vertex color cluster. A PolygonMesh needs to be passed as argument.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetVertexColors0_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh geo = args[0];
	CGeometryAccessor ga = geo.GetGeometryAccessor();
	CRefArray uvs = ga.GetVertexColors();
	ClusterProperty uv = uvs[0];
	CFloatArray vcvalues;
	uv.GetValues(vcvalues);
	ctxt.PutAttribute( L"ReturnValue", vcvalues );
	return CStatus::OK;
}
CALLBACK CGA_GetWeights0_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	command.PutDescription(L"Returns Weight values as CFloatArray of the first UV cluster. A PolygonMesh needs to be passed as argument.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetWeights0_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh geo = args[0];
	CGeometryAccessor ga = geo.GetGeometryAccessor();
	CRefArray envWeights = ga.GetEnvelopeWeights();
	EnvelopeWeight envWeight = envWeights[0];
	CFloatArray weights;
	envWeight.GetValues(weights);
	ctxt.PutAttribute( L"ReturnValue", weights);
	return CStatus::OK;
}

CALLBACK CGA_GetWeightsZE_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	command.PutDescription(L"Returns ( (elemcount), (weights), (deformerindices), (deformernames) ). A PolygonMesh needs to be passed as argument.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetWeightsZE_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh geo = args[0];
	CGeometryAccessor ga = geo.GetGeometryAccessor();
	CRefArray envWeights = ga.GetEnvelopeWeights();
	EnvelopeWeight envWeight = envWeights[0];
	CFloatArray weights;
	envWeight.GetValues(weights);
	long valsize = envWeight.GetValueSize();
	xsi.LogMessage( CString(valsize));
	long geosize = weights.GetCount() / valsize;
	// Declare arrays.
	CValueArray def_names(valsize);

	CRefArray deformers = envWeight.GetDeformers();
	def_names.Resize(deformers.GetCount());
	for(long j=0; j<deformers.GetCount(); j++) {
		SIObject siobj(deformers[j]);
		def_names[j] = siobj.GetName();
	}
	CValueArray weights_defs(3);
	weights_defs[0] = valsize;
	weights_defs[1] = weights;
	weights_defs[2] = def_names;
	ctxt.PutAttribute( L"ReturnValue", weights_defs);
	return CStatus::OK;
}

CALLBACK CGA_GetNodesPerPoint_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command command;
	command = ctxt.GetSource();
	ArgumentArray arguments;
	arguments = command.GetArguments();
	arguments.Add(L"polyMesh");
	command.PutDescription(L"Returns Nodes per Point. A PolygonMesh needs to be passed as argument.");
	command.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetNodesPerPoint_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh geo = args[0];
	CGeometryAccessor ga = geo.GetGeometryAccessor();
	CValueArray ordered;
	// get poly node indices
	CLongArray nodeindices;
	ga.GetNodeIndices(nodeindices);
	// get poly vert indices
	CLongArray vertindices;
	ga.GetVertexIndices(vertindices);
	xsi.LogMessage( CString(nodeindices.GetCount()));
	xsi.LogMessage( CString(vertindices.GetCount()));
	ordered.Resize( nodeindices.GetCount() );
	for(long j=0; j<nodeindices.GetCount(); j++) {
		long vertindex = vertindices[j];
		long nodeindex = nodeindices[j];
		ordered[nodeindex] = vertindex;
	}
	ctxt.PutAttribute( L"ReturnValue", ordered);
	return CStatus::OK;
}