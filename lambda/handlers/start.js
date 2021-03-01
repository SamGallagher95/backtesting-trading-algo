const aws = require("aws-sdk");

module.exports.index = function (event, context) {
  try {
    const ec2 = new aws.EC2({ region: "us-east-1" });
    ec2.runInstances(
      {
        MinCount: 1,
        MaxCount: 1,
        LaunchTemplate: {
          LaunchTemplateId: "lt-068610880f56280b5",
        },
      },
      (err, data) => {
        if (err) throw err;
        console.log(data);
      }
    );
  } catch (err) {
    console.log("There was an error");
    console.log(err);
  }
};
